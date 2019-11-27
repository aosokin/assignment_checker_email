# Something in the lines of http://stackoverflow.com/questions/348630/how-can-i-download-all-emails-with-attachments-from-gmail
# Make sure you have IMAP enabled in your gmail settings.
# Right now it won't download same file name twice even if their contents are different.

import email, imaplib
import smtplib
import os
from email.mime.text import MIMEText

import timezone


def connect_gmail( gmail_address, gmail_password ):
    imap_session = imaplib.IMAP4_SSL('imap.gmail.com')
    exit_code, account_details = imap_session.login(gmail_address,  gmail_password)
    if exit_code != 'OK':
        raise RuntimeError(f"Cannot connect to {gmail_address}")
    return imap_session

def disconnect_gmail( imap_session ):
    imap_session.close()
    imap_session.logout()

def get_email_body(mail):
    body = ""
    if mail.is_multipart():
        for part in mail.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))

            # skip any text/plain (txt) attachments
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)  # decode
                break
    # not multipart - i.e. plain text, no attachments, keeping fingers crossed
    else:
        body = mail.get_payload(decode=True)
    return body

def get_email_attachments(mail):
    attachments = []
    for part in mail.walk():
        if part.is_multipart():
            continue
        if part.get('Content-Disposition') is None:
            continue
        # if we get here than we have found a file
        file_name = part.get_filename()
        if bool(file_name):
            file_content = part.get_payload(decode=True)
            attachments.append( {'file_name' : file_name, 'file_content': file_content} )
    return attachments

def receive_emails_gmail( gmail_address, gmail_password, gmail_label ):
    emails_received = []
    try:
        imap_session = connect_gmail( gmail_address, gmail_password )

        imap_session.select( gmail_label )
        # typ, data = imap_session.search(None, 'ALL') # receive all e-mails
        exit_code, data = imap_session.search(None, '(UNSEEN)') # receive only unread e-mails
        if exit_code != 'OK':
            raise RuntimeError(f"Error while searching e-mails from {gmail_address}")

        # Iterating over all emails
        for msgId in data[0].split():
            exit_code, message_parts = imap_session.fetch(msgId, '(RFC822)') # magic sequence
            if exit_code != 'OK':
                raise RuntimeError(f"Error fetching mail from {gmail_address}")

            # parsing the new e-mail
            email_current = {}

            # get the whole mail in one object
            email_body = message_parts[0][1]
            email_body = email_body.decode("utf-8")
            mail = email.message_from_string(email_body, policy=email.policy.default)

            # sender address
            email_current['From'] = email.utils.parseaddr( mail['From'] )[1]
            # subject
            email_current['Subject'] = mail['Subject']
            # receival time
            email_current['Time'] = timezone.make_email_time_string(email.utils.parsedate_tz(mail['Date']))
            # e-mail body
            email_current['Message'] = get_email_body(mail)
            # attachements
            email_current['Attachments'] = get_email_attachments(mail)
            # CC addresses
            email_current['CCed'] = []
            if 'Cc' in mail:
                emails_cced = mail['Cc'].split(', ')
                if emails_cced:
                    for cur_email in emails_cced:
                        email_current['CCed'].append( email.utils.parseaddr( cur_email )[1] )

            # save the e-mail
            emails_received.append( email_current )

        # close connection to the server
        disconnect_gmail( imap_session )
        exit_message = 'OK'
    except Exception as e:
        exit_message = f"ERROR: could not download e-mails from {gmail_address}, label: {gmail_label}, \n Error:\n {str(e)}"

    return exit_message, emails_received


def create_path(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def save_unsent_email(message, failed_emails_path):
    email_index = 0
    email_path = None
    create_path(failed_emails_path)
    while not email_path or os.path.exists( email_path ):
        email_index+=1
        email_path = os.path.join(failed_emails_path, 'failed_email_%04d.txt'%(email_index))

    with open(email_path, "w") as text_file:
        text_file.write(message)


def send_email_gmail(gmail_address, gmail_password, recipient, subject, body, failed_emails_path = 'unsent_emails'):
    FROM = gmail_address
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    message = email.mime.multipart.MIMEMultipart('alternative')
    message['Subject'] = str(email.header.Header(SUBJECT, 'utf-8'))
    message['From'] = gmail_address
    message['To'] = TO

    textpart = MIMEText(TEXT, 'plain', 'UTF-8')
    message.attach(textpart)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_address, gmail_password)
        server.sendmail(FROM, TO, message.as_string())
        server.close()
        exit_message = 'OK'
    except Exception as e:
        save_unsent_email(message, failed_emails_path)
        exit_message = "ERROR: failed to send mail from " +  gmail_address +  ' to '+  recipient + '\n' + "Error:\n" + str(e)

    return exit_message


def reply_email_gmail( gmail_address, gmail_password, email_received, reply_text = '', emails_cc = None, failed_emails_path = 'unsent_emails'):
    # Prepare actual message
    toaddr = [email_received['From']]

    message = email.mime.multipart.MIMEMultipart('alternative')
    message['Subject'] = str(email.header.Header('Re: '+email_received['Subject'], 'utf-8'))
    message['From'] = gmail_address
    message['To'] = email_received['From']

    if emails_cc:
        toaddr = toaddr + emails_cc
        message['Cc'] = ",".join(emails_cc)

    textpart = MIMEText(reply_text, 'plain', 'UTF-8')
    message.attach(textpart)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, toaddr, message.as_string())
        server.close()
        exit_message = 'OK'
    except  Exception as e:
        save_unsent_email(message, failed_emails_path)
        exit_message = "ERROR: failed to send mail from " +  gmail_address +  ' to '+  email_received['From'] + '\n' + "Error:\n" + str(e)

    return exit_message


def replyall_email_gmail( gmail_address, gmail_password, email_received, reply_text = '', emails_cc = None, failed_emails_path = 'unsent_emails'):
    if 'CCed' in email_received:
        return reply_email_gmail( gmail_address, gmail_password, email_received, reply_text, emails_cc = email_received['CCed'], failed_emails_path = failed_emails_path)
    else:
        return reply_email_gmail( gmail_address, gmail_password, email_received, reply_text, failed_emails_path = failed_emails_path)


def forward_email_gmail( gmail_address, gmail_password, target_address, email_received, forward_text = '', emails_cc = None, failed_emails_path = 'unsent_emails'):
    # Prepare actual message
    toaddr = [target_address]
    cc_part_message = ''
    if emails_cc:
        cc_part_message = "CC: %s\n" % ",".join(emails_cc)
        toaddr = toaddr + emails_cc

    message = """From: %s\nTo: %s\n%sSubject: %s\n\n%s-------\n%s
    """ % (gmail_address, target_address, cc_part_message, 'Fwd: '+email_received['Subject'], forward_text, email_received['Message'])

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, target_address, message)
        server.close()
        exit_message = 'OK'
    except:
        save_unsent_email(message, failed_emails_path)
        exit_message = "ERROR: failed to send mail from " +  gmail_address +  ' to '+  target_address

    return exit_message
    