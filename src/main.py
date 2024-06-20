import imaplib
import email
from email.policy import default
import pandas as pd
import argparse
import getpass
from sklearn.feature_extraction.text import CountVectorizer
from bs4 import BeautifulSoup
import csv
import re

def decode_bytes(byte_content):
    encodings = ['utf-8', 'latin-1', 'iso-8859-1']
    for enc in encodings:
        try:
            return byte_content.decode(enc)
        except UnicodeDecodeError:
            continue
    return byte_content.decode('utf-8', errors='replace')

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

def fetch_spam_emails(mail, limit=None):
    print("Selecting folder: [Gmail]/Spam")
    mail.select('[Gmail]/Spam')
    print("Searching for emails in [Gmail]/Spam...")
    status, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()
    print(f"Found {len(email_ids)} emails in [Gmail]/Spam.")

    email_texts = []
    count = 0
    for e_id in email_ids:
        if limit and count >= limit:
            break
        print(f"Fetching email ID: {e_id} from [Gmail]/Spam")
        status, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                print(f"Processing email ID: {e_id}")
                msg = email.message_from_bytes(response_part[1], policy=default)
                email_content = ""
                if msg.is_multipart():
                    for part in msg.iter_parts():
                        if part.get_content_type() == 'text/plain':
                            email_content = decode_bytes(part.get_payload(decode=True))
                        elif part.get_content_type() == 'text/html':
                            email_content = extract_text_from_html(decode_bytes(part.get_payload(decode=True)))
                else:
                    if msg.get_content_type() == 'text/plain':
                        email_content = decode_bytes(msg.get_payload(decode=True))
                    elif msg.get_content_type() == 'text/html':
                        email_content = extract_text_from_html(decode_bytes(msg.get_payload(decode=True)))
                email_texts.append(email_content)
        count += 1

    return email_texts

def main():
    parser = argparse.ArgumentParser(description='Extract spam emails from a Gmail account.')
    parser.add_argument('email', type=str, help='Your Gmail address')
    parser.add_argument('--limit', type=int, default=1000, help='Limit the number of emails to fetch')
    args = parser.parse_args()

    password = getpass.getpass(prompt='Enter your Gmail password: ')

    SERVER = 'imap.gmail.com'

    print("Connecting to the server...")
    mail = imaplib.IMAP4_SSL(SERVER)
    mail.login(args.email, password)
    print("Connected.")

    email_texts = fetch_spam_emails(mail, limit=args.limit)

    print("Closing connection to the server...")
    mail.close()
    mail.logout()
    print("Disconnected.")

    # Convert emails to a DataFrame
    print("Creating DataFrame...")
    df = pd.DataFrame({'EmailText': email_texts})

    # Use CountVectorizer to create features based on word frequency
    vectorizer = CountVectorizer(token_pattern=r'\b[A-Za-z]+\b')  # Only consider words with alphabetic characters
    X = vectorizer.fit_transform(df['EmailText'])

    # Create a DataFrame with the features
    feature_names = vectorizer.get_feature_names_out()
    df_features = pd.DataFrame(X.toarray(), columns=feature_names)

    # Add the target column
    df_features['y'] = 1

    # Save the DataFrame to a CSV file
    output_file = 'result/spam_emails_with_features.csv'
    print(f"Saving to CSV file: {output_file}")
    df_features.to_csv(output_file, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"Number of emails: {len(df_features)}")
    print(f"Number of features: {len(df_features.columns) - 1}")
    print(f"Extraction completed! Dataset with features has been saved in '{output_file}'.")

if __name__ == '__main__':
    main()