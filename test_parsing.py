#!/usr/bin/env python3
"""
Simple test script to verify the email parsing logic works correctly.
"""

import json

def parse_foilboi_email_body(email_body):
    """Parse the structured email body from foilboi@gmail.com"""
    try:
        # The email body contains structured data in a specific format
        # We need to extract key-value pairs from the text
        
        task_data = {}
        
        # Split the email body into lines
        lines = email_body.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('---'):
                i += 1
                continue
                
            # Look for key-value patterns
            if ':' in line:
                # Handle different formats
                if line.startswith('CustomerName:'):
                    task_data['CustomerName'] = line.split(':', 1)[1].strip().rstrip(',')
                elif '"custemail"' in line:
                    # Extract email from "custemail": richard.genet@gmail.com ,
                    email_match = line.split('"custemail"')[1].strip()
                    if ':' in email_match:
                        email = email_match.split(':', 1)[1].strip().rstrip(',').strip('"')
                        task_data['custemail'] = email
                elif '"Posted"' in line:
                    task_data['Posted'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"DueDate"' in line:
                    task_data['DueDate'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"Task"' in line:
                    task_data['Task'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"description"' in line:
                    task_data['description'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"Category"' in line:
                    task_data['Category'] = line.split(':', 1)[1].strip().rstrip(',').strip('"{}')
                elif '"FullAddress"' in line:
                    task_data['FullAddress'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"Task Budget"' in line:
                    task_data['Task Budget'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"State"' in line:
                    task_data['State'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"vendors"' in line:
                    # Vendors section is multi-line, so we need to capture all content until the closing brace
                    vendors_start = line.find('"vendors"')
                    if vendors_start != -1:
                        # Get the initial content from this line
                        initial_content = line[vendors_start:].split(':', 1)[1].strip()
                        vendors_content = [initial_content]
                        
                        # Continue reading lines until we find the closing brace
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            vendors_content.append(next_line)
                            
                            # Check if this line contains the closing brace
                            if '}' in next_line:
                                break
                            i += 1
                        
                        # Join all the vendors content
                        task_data['vendors'] = '\n'.join(vendors_content)
                        i += 1  # Move to next line after processing vendors
                        continue
            
            i += 1
        
        # Validate that we have the essential fields
        if not task_data.get('custemail') or not task_data.get('Task'):
            print(f'❌ Missing essential fields in parsed task data: {task_data}')
            return None
        
        print(f'✅ Successfully parsed task data: {json.dumps(task_data, indent=2)}')
        return task_data
        
    except Exception as error:
        print(f'❌ Error parsing foilboi email body: {error}')
        return None

def test_parsing():
    """Test the email parsing with the actual format"""
    
    print("🧪 Testing email parsing function...")
    
    # Test with the actual email format
    email_body = """CustomerName: Richard Genet,
    "custemail": richard.genet@gmail.com ,
    "Posted": empty,
    "DueDate": 6/27/2025, 12:00:00 AM,
    "Task": t 1035,
    "description": d,
    "Category": {Appraisal},
    "FullAddress": ,
    "Task Budget":1 ,
    "State": GA,
    "vendors": {I found three reputable vendors within 10 miles of the location who specialize in appraisals and have consistently high feedback ratings:

1. Best Appraisals LLC - Located at 123 Main Street, Anytown. With an average feedback rating of 4.9, Best Appraisals LLC has a proven track record of providing accurate and thorough appraisals in the area.

2. Elite Appraisal Services - Situated at 456 Oak Avenue, Nearby City. Elite Appraisal Services boasts an impressive average feedback rating of 4.8. Their team of experienced professionals is known for their attention to detail and timely service.

3. Superior Valuations Inc. - Found at 789 Elm Street, Local Town. Superior Valuations Inc. has an average feedback rating of 4.7. They are known for their comprehensive appraisal reports and commitment to customer satisfaction.

These vendors are well-regarded in the community and are equipped to handle the task with excellence. If you'd like, I can reach out to them with the task details for their approval.}"""
    
    print(f"📧 Test email body: {email_body[:200]}...")
    
    parsed_data = parse_foilboi_email_body(email_body)
    
    if parsed_data:
        print("✅ Email parsing successful!")
        
        # Verify key fields
        expected_fields = ['CustomerName', 'custemail', 'Task', 'Category', 'State']
        for field in expected_fields:
            if field in parsed_data:
                print(f"✅ Found {field}: {parsed_data[field]}")
            else:
                print(f"❌ Missing {field}")
        
        # Test creating task title
        customer_name = parsed_data.get('CustomerName', '').strip()
        task_number = parsed_data.get('Task', '').strip()
        category = parsed_data.get('Category', '').strip()
        
        task_title = f"Task {task_number} - {category} - {customer_name}"
        print(f"📋 Generated task title: {task_title}")
        
        # Test creating initial response for LangGraph
        initial_response = f"""
Task Request Details:
- Customer: {customer_name} ({parsed_data.get('custemail')})
- Task Number: {task_number}
- Category: {category}
- Description: {parsed_data.get('description')}
- Due Date: {parsed_data.get('DueDate')}
- State: {parsed_data.get('State')}
- Vendors: {parsed_data.get('vendors', '')[:100]}...

Please help me process this task request.
"""
        print(f"💬 Initial response for LangGraph: {initial_response[:200]}...")
        
    else:
        print("❌ Email parsing failed!")

if __name__ == "__main__":
    test_parsing() 