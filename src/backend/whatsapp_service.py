import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class WhatsAppService:

    def __init__(self):
        self.driver = None

    def start_whatsapp(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.driver.get("https://web.whatsapp.com")
        print("Scan QR Code to login...")
        time.sleep(15)   # wait for QR scan

    def send_message(self, number, message):
        try:
            # Check if driver is initialized
            if self.driver is None:
                error_msg = "WhatsApp session not started. Please call /start endpoint first to initialize WhatsApp Web."
                print(error_msg)
                return False
            
            # Format phone number (remove spaces, dashes, plus sign, etc.)
            # Keep only digits - WhatsApp Web needs country code + number without + sign
            number = str(number).strip()
            # Remove common formatting characters but keep digits
            number = ''.join(filter(str.isdigit, number))
            
            if not number:
                print(f"Invalid phone number format")
                return False
            
            url = f"https://web.whatsapp.com/send?phone={number}&text={message}"
            self.driver.get(url)
            
            # Wait for page to load and message input to be available
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for the message input box to be present and visible
            message_input = None
            try:
                # Try multiple selectors for the message input box
                selectors = [
                    "//div[@contenteditable='true'][@data-tab='10']",
                    "//div[@contenteditable='true'][@role='textbox']",
                    "//div[@contenteditable='true']",
                    "//div[contains(@class, 'selectable-text')]//div[@contenteditable='true']"
                ]
                
                for selector in selectors:
                    try:
                        message_input = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                        if message_input and message_input.is_displayed():
                            print(f"Found message input with selector: {selector}")
                            break
                    except TimeoutException:
                        continue
                
                if not message_input:
                    raise TimeoutException("Could not find message input box")
                
            except TimeoutException:
                print(f"Error: Could not find message input box for {number}")
                return False
            
            # Wait a bit for the page to fully load and message to be populated
            time.sleep(4)
            
            # Verify message is in the input (sometimes URL parameter doesn't populate)
            try:
                input_text = message_input.text.strip()
                if not input_text or message not in input_text:
                    # Message not auto-populated, type it manually
                    print(f"Message not auto-populated, typing manually...")
                    message_input.clear()
                    message_input.send_keys(message)
                    time.sleep(1)
            except:
                # If we can't read the text, try typing anyway
                try:
                    message_input.send_keys(message)
                    time.sleep(1)
                except:
                    pass
            
            # Try multiple methods to send the message
            sent = False
            
            # Method 1: Try clicking send button with multiple selectors
            send_selectors = [
                "//span[@data-icon='send']",
                "//button[@aria-label='Send']",
                "//span[contains(@data-icon, 'send')]",
                "//button[contains(@title, 'Send')]",
                "//span[@role='button'][@data-icon='send']"
            ]
            
            for selector in send_selectors:
                try:
                    send_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    # Try JavaScript click first (more reliable)
                    self.driver.execute_script("arguments[0].click();", send_btn)
                    print(f"Clicked send button using selector: {selector}")
                    sent = True
                    break
                except (TimeoutException, NoSuchElementException):
                    continue
                except Exception as e:
                    print(f"Error clicking send button with selector {selector}: {str(e)}")
                    continue
            
            # Method 2: If button click didn't work, try pressing Enter key
            if not sent:
                try:
                    print("Trying to send using Enter key...")
                    message_input.send_keys(Keys.ENTER)
                    sent = True
                    print("Sent using Enter key")
                except Exception as e:
                    print(f"Error sending with Enter key: {str(e)}")
            
            # Method 3: Try JavaScript to trigger send
            if not sent:
                try:
                    print("Trying JavaScript send...")
                    self.driver.execute_script("""
                        var sendButton = document.querySelector('span[data-icon="send"]');
                        if (sendButton) {
                            sendButton.click();
                        } else {
                            var buttons = document.querySelectorAll('button[aria-label="Send"]');
                            if (buttons.length > 0) buttons[0].click();
                        }
                    """)
                    sent = True
                    print("Sent using JavaScript")
                except Exception as e:
                    print(f"Error with JavaScript send: {str(e)}")
            
            # Wait for message to be sent
            time.sleep(3)
            
            if sent:
                print(f"✓ Message sent successfully to {number}")
                return True
            else:
                print(f"✗ Failed to send message to {number} - all methods failed")
                return False
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error sending message to {number}: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error sending message to {number}: {str(e)}")
            return False

    def send_bulk(self, excel_path, message):
        try:
            # Check if driver is initialized
            if self.driver is None:
                error_msg = "WhatsApp session not started. Please call /start endpoint first to initialize WhatsApp Web."
                print(f"Error in bulk send: {error_msg}")
                return {"success": 0, "failed": 0, "total": 0, "error": error_msg}
            
            # Read the Excel file
            df = pd.read_excel(excel_path)
            
            # Check if DataFrame is empty
            if df.empty:
                error_msg = "Excel file is empty. Please add phone numbers to the file."
                print(f"Error in bulk send: {error_msg}")
                return {"success": 0, "failed": 0, "total": 0, "error": error_msg}
            
            # Try to find the phone number column (case-insensitive)
            # Common column names: number, numbers, phone, phone_number, mobile, contact, etc.
            possible_columns = ['number', 'numbers', 'phone', 'phone_number', 'mobile', 'contact', 'phoneNumber', 'Phone', 'Number', 'Numbers']
            
            number_column = None
            
            # First, try exact match (case-sensitive)
            for col in possible_columns:
                if col in df.columns:
                    number_column = col
                    break
            
            # If not found, try case-insensitive exact match
            if number_column is None:
                df_columns_lower = [col.lower().strip() for col in df.columns]
                for possible_col in possible_columns:
                    if possible_col.lower() in df_columns_lower:
                        idx = df_columns_lower.index(possible_col.lower())
                        number_column = df.columns[idx]
                        break
            
            # If still not found, try substring match (contains "number" or "phone")
            if number_column is None:
                for col in df.columns:
                    col_lower = str(col).lower().strip()
                    if 'number' in col_lower or 'phone' in col_lower or 'mobile' in col_lower:
                        number_column = col
                        print(f"Found column by substring match: '{col}'")
                        break
            
            # If still not found, show available columns
            if number_column is None:
                available_columns = list(df.columns)
                error_msg = f"Could not find a phone number column. Available columns: {available_columns}. Please ensure one column contains 'number', 'phone', or 'mobile' in its name (e.g., 'number', 'numbers', 'phone', 'phone_number')."
                print(f"Error in bulk send: {error_msg}")
                return {"success": 0, "failed": 0, "total": 0, "error": error_msg}
            
            # Get numbers from the column
            numbers = df[number_column].tolist()
            
            # Filter out NaN/None values
            numbers = [num for num in numbers if pd.notna(num) and str(num).strip()]
            
            if not numbers:
                error_msg = "No valid phone numbers found in the Excel file."
                print(f"Error in bulk send: {error_msg}")
                return {"success": 0, "failed": 0, "total": 0, "error": error_msg}
            
            total = len(numbers)
            success_count = 0
            failed_count = 0
            
            print(f"Starting bulk send to {total} numbers...")
            print(f"Using column: '{number_column}'")
            
            for idx, num in enumerate(numbers, 1):
                print(f"[{idx}/{total}] Sending to {num}...")
                
                if self.send_message(num, message):
                    success_count += 1
                    print(f"✓ Successfully sent to {num}")
                else:
                    failed_count += 1
                    print(f"✗ Failed to send to {num}")
                
                # Add delay between messages to avoid rate limiting
                # Wait longer between messages (5-7 seconds)
                if idx < total:  # Don't wait after the last message
                    time.sleep(5)
            
            print(f"\nBulk send completed!")
            print(f"Success: {success_count}, Failed: {failed_count}, Total: {total}")
            
            return {"success": success_count, "failed": failed_count, "total": total}
            
        except KeyError as e:
            error_msg = f"Column error: {str(e)}. Please check your Excel file has the correct column name."
            print(f"Error in bulk send: {error_msg}")
            return {"success": 0, "failed": 0, "total": 0, "error": error_msg}
        except Exception as e:
            error_msg = f"Error reading Excel file: {str(e)}"
            print(f"Error in bulk send: {error_msg}")
            return {"success": 0, "failed": 0, "total": 0, "error": error_msg}
