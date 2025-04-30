import imaplib  # For IMAP protocol communication with email servers
import email  # For parsing email messages
from email.header import decode_header  # For decoding email headers
import json  # For JSON file operations
from datetime import datetime  # For timestamping
import pandas as pd  # For data manipulation and CSV export
import os  # For file system operations
from dotenv import load_dotenv  # For loading environment variables
import streamlit as st  # For building the web interface

# Load environment variables from .env file if it exists
load_dotenv()

class EmailReaderAgent:
    def __init__(self):
        # Initialize connection variables
        self.imap_server = None  # Will store the IMAP server address
        self.mail = None  # Will store the IMAP connection object
        
        # Define email categories and their identifying keywords
        self.categories = {
            'Promotions': ['offer', 'deal', 'discount', 'promo', 'sale', 'coupon'],
            'Social': ['facebook', 'twitter', 'linkedin', 'instagram', 'social'],
            'Work': ['work', 'job', 'career', 'meeting', 'project', 'team'],
            'Personal': ['family', 'friend', 'personal', 'mom', 'dad']
        }
    
    def connect(self, email_provider, email, password):
        """Connect to IMAP server using provided credentials"""
        # Set IMAP server based on provider
        if email_provider.lower() == 'gmail':
            self.imap_server = 'imap.gmail.com'
        elif email_provider.lower() == 'outlook':
            self.imap_server = 'imap-mail.outlook.com'
        else:
            raise ValueError("Unsupported email provider. Use 'Gmail' or 'Outlook'.")
        
        try:
            # Establish SSL-secured IMAP connection
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            # Login with provided credentials
            self.mail.login(email, password)
            st.success("Successfully connected to email server.")
            return True
        except Exception as e:
            st.error(f"Failed to connect: {e}")
            return False
    
    def fetch_emails(self, limit=50):
        """Fetch latest emails from inbox with optional limit"""
        if not self.mail:
            st.warning("Not connected to server.")
            return []
        
        # Select the INBOX folder
        self.mail.select('INBOX')
        # Search for all emails
        status, messages = self.mail.search(None, 'ALL')
        if status != 'OK':
            st.warning("No messages found.")
            return []
        
        # Get the latest 'limit' email IDs
        email_ids = messages[0].split()[-limit:]
        emails = []
        
        # Process each email
        for email_id in email_ids:
            try:
                # Fetch the email by ID
                status, msg_data = self.mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                # Parse the raw email data
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Extract and store email details
                email_details = self._parse_email(msg)
                emails.append(email_details)
            except Exception as e:
                st.warning(f"Error processing email {email_id}: {e}")
        
        return emails
    
    def _parse_email(self, msg):
        """Extract and parse key details from an email message"""
        # Decode subject (handles different encodings)
        subject, encoding = decode_header(msg["Subject"])[0] if msg["Subject"] else (None, None)
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else 'utf-8')
        
        # Decode sender information
        sender, encoding = decode_header(msg.get("From"))[0] if msg.get("From") else (None, None)
        if isinstance(sender, bytes):
            sender = sender.decode(encoding if encoding else 'utf-8')
        
        # Get email date
        date = msg.get("Date")
        
        # Extract email body
        body = ""
        if msg.is_multipart():  # Handle multipart emails (with attachments, etc.)
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Look for plain text parts that aren't attachments
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body = part.get_payload(decode=True).decode()
                    break
        else:  # Handle simple emails
            body = msg.get_payload(decode=True).decode()
        
        # Create a preview snippet (first 100 characters)
        snippet = body[:100] + '...' if len(body) > 100 else body
        
        # Return structured email data
        return {
            'sender': sender,
            'subject': subject,
            'date': date,
            'snippet': snippet,
            'body': body
        }
    
    def categorize_email(self, email_data):
        """Categorize email based on keywords in subject and snippet"""
        # Combine subject and snippet for keyword searching
        email_text = f"{email_data['subject']} {email_data['snippet']}".lower()
        
        # Check each category's keywords
        for category, keywords in self.categories.items():
            if any(keyword in email_text for keyword in keywords):
                return category
        
        # Default category if no matches found
        return 'Uncategorized'
    
    def process_emails(self, limit=50):
        """Fetch emails and categorize them"""
        emails = self.fetch_emails(limit)
        processed_emails = []
        
        for email_data in emails:
            # Categorize each email
            category = self.categorize_email(email_data)
            processed_emails.append({
                **email_data,  # Include all original email data
                'category': category  # Add the category
            })
            
            # Optional notification for important categories
            if category in ['Work']:
                st.info(f"New important email: {email_data['subject']}")
        
        return processed_emails
    
    def save_results(self, emails, format='json'):
        """Save processed emails to a file in specified format"""
        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"email_results_{timestamp}.{format}"
        
        # Save in requested format
        if format == 'json':
            with open(filename, 'w') as f:
                json.dump(emails, f, indent=2)
        elif format == 'csv':
            df = pd.DataFrame(emails)
            df.to_csv(filename, index=False)
        elif format == 'txt':
            with open(filename, 'w') as f:
                for email in emails:
                    f.write(f"From: {email['sender']}\n")
                    f.write(f"Subject: {email['subject']}\n")
                    f.write(f"Date: {email['date']}\n")
                    f.write(f"Category: {email['category']}\n")
                    f.write(f"Snippet: {email['snippet']}\n")
                    f.write("\n" + "-"*50 + "\n\n")
        else:
            raise ValueError("Unsupported format. Use 'json', 'csv', or 'txt'.")
        
        st.success(f"Results saved to {filename}")
        return filename
    
    def disconnect(self):
        """Close the IMAP connection"""
        if self.mail:
            self.mail.logout()
            st.info("Disconnected from email server.")

def main():
    """Main function to run the Streamlit application"""
    st.title("📧 Email Reader Agent")
    st.markdown("Connect to your email account to fetch and categorize your emails.")
    
    # Initialize session state variables
    if 'emails' not in st.session_state:
        st.session_state.emails = None  # Will store fetched emails
    if 'agent' not in st.session_state:
        st.session_state.agent = EmailReaderAgent()  # Create agent instance
    
    # Sidebar for connection settings
    with st.sidebar:
        st.header("Email Settings")
        # Provider selection
        email_provider = st.selectbox("Email Provider", ["Gmail", "Outlook"])
        # Email and password inputs
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        
        # Connect button
        if st.button("Connect"):
            with st.spinner("Connecting to email server..."):
                if st.session_state.agent.connect(email_provider, email, password):
                    st.session_state.connected = True
                else:
                    st.session_state.connected = False
        
        # Disconnect button
        if st.button("Disconnect"):
            st.session_state.agent.disconnect()
            st.session_state.connected = False
            st.session_state.emails = None
    
    # Main application content
    if st.session_state.get('connected'):
        st.success("Connected to email server")
        
        # Slider to select how many emails to fetch
        limit = st.slider("Number of emails to fetch", 1, 100, 20)
        
        # Fetch emails button
        if st.button("Fetch Emails"):
            with st.spinner(f"Fetching {limit} emails..."):
                st.session_state.emails = st.session_state.agent.process_emails(limit=limit)
        
        # Display results if emails were fetched
        if st.session_state.emails:
            st.subheader(f"Email Summary ({len(st.session_state.emails)} emails)")
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(st.session_state.emails)
            # Count emails by category
            category_counts = df['category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']
            
            # Create two columns for layout
            col1, col2 = st.columns(2)
            
            # Left column: Category distribution chart
            with col1:
                st.write("### Categories Distribution")
                st.bar_chart(category_counts.set_index('Category'))
            
            # Right column: Recent emails table
            with col2:
                st.write("### Recent Emails")
                st.dataframe(df[['sender', 'subject', 'category']].head())
            
            # Email details section
            st.subheader("Email Details")
            # Dropdown to select specific email
            selected_email = st.selectbox(
                "Select an email to view details",
                options=range(len(st.session_state.emails)),
                format_func=lambda i: f"{st.session_state.emails[i]['subject']} - {st.session_state.emails[i]['sender']}"
            )
            
            # Display details of selected email
            if selected_email is not None:
                email = st.session_state.emails[selected_email]
                st.markdown(f"**From:** {email['sender']}")
                st.markdown(f"**Subject:** {email['subject']}")
                st.markdown(f"**Date:** {email['date']}")
                st.markdown(f"**Category:** {email['category']}")
                st.markdown(f"**Snippet:** {email['snippet']}")
                
                # Display full email body in scrollable area
                st.markdown("**Full Body:**")
                with st.container():
                    st.text_area(
                        "Body",
                        value=email['body'],
                        height=300,
                        key=f"body_{selected_email}",
                        disabled=True
                    )
                st.markdown("---")
            
            # Save options section
            st.subheader("Save Results")
            # Format selection
            save_format = st.radio("Select format to save", ["json", "csv", "txt"])
            
            # Save button
            if st.button("Save Emails"):
                filename = st.session_state.agent.save_results(st.session_state.emails, format=save_format)
                # Provide download link
                with open(filename, "rb") as f:
                    st.download_button(
                        label="Download File",
                        data=f,
                        file_name=filename,
                        mime="text/plain" if save_format == "txt" else "application/octet-stream"
                    )
    else:
        # Show message when not connected
        st.warning("Please connect to your email account using the sidebar.")

if __name__ == "__main__":
    main()  # Run the application