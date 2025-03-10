import re
import datetime
import pandas as pd
from striprtf.striprtf import rtf_to_text

# Load RTF file and convert it to plain text
def load_rtf(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        rtf_content = f.read()
    return rtf_to_text(rtf_content)  # Converts RTF to plain text

# Extract enter logs
def parse_entry_logs(text):
    logs = {}

    entry_pattern = re.compile(
        r"(\w{3} \d{2} \d{2}:\d{2}:\d{2} (?:AM|PM))\n(?:\n)?\[DEBUG\] Storing Prolific ID: ([a-f0-9]+), assigned: (\w+)",
        re.MULTILINE
    )

    print("\n--- Parsing Enter Logs ---")
    for match in entry_pattern.finditer(text):
        timestamp, prolific_id, expert = match.groups()
        if prolific_id not in logs:
            logs[prolific_id] = {
                "Prolific ID": prolific_id,
                "Assigned Expert": expert,
                "Enter Time": timestamp,
                "Exit Time": None,
                "Total Time": None
            }
            print(f"Found Entry Log: ID={prolific_id}, Expert={expert}, Time={timestamp}")
        else:
            print(f"Duplicate Entry Log Skipped: ID={prolific_id}")

    return logs

# Extract exit logs using the "[DEBUG] final-answer" line
def parse_exit_logs(text, logs):
    print("\n--- Parsing Exit Logs ---")
    
    lines = text.split("\n")
    for i in range(2, len(lines)):  # Start from 2 to avoid index errors
        if "[DEBUG] final-answer" in lines[i]:  # Identify the final answer line
            prolific_id_match = re.search(r"\[DEBUG\] final-answer => ID is ([a-f0-9]+)", lines[i])
            if prolific_id_match:
                prolific_id = prolific_id_match.group(1)
                if prolific_id in logs:
                    exit_timestamp = lines[i - 2].strip()  # Two lines above contains the timestamp
                    logs[prolific_id]["Exit Time"] = exit_timestamp
                    print(f"Matched Exit Log -> ID={prolific_id}, Time={exit_timestamp}")
                else:
                    print(f"Warning: Exit Log Found for Unmatched ID {prolific_id}!")
    
    return logs

# Convert timestamps and calculate total time spent
def calculate_durations(logs):
    print("\n--- Calculating Durations ---")
    for log in logs.values():
        if log["Enter Time"] and log["Exit Time"]:
            try:
                enter_dt = datetime.datetime.strptime(log["Enter Time"], "%b %d %I:%M:%S %p")
                exit_dt = datetime.datetime.strptime(log["Exit Time"], "%b %d %I:%M:%S %p")
                duration = exit_dt - enter_dt
                log["Total Time"] = str(duration)
                print(f"ID={log['Prolific ID']}: Duration={duration}")
            except Exception as e:
                print(f"Error parsing time for ID={log['Prolific ID']}: {e}")
        else:
            print(f"Skipping duration calculation for ID={log['Prolific ID']} (Missing timestamps)")
    return list(logs.values())

# Save data to an Excel-compatible file
def save_to_excel(logs, output_file):
    df = pd.DataFrame(logs)
    df.to_excel(output_file, index=False)
    print(f"\n--- Data Saved to {output_file} ---")

# Main function
def process_rtf_logs(input_file, output_file):
    print(f"\n=== Processing {input_file} ===")
    text = load_rtf(input_file)

    logs = parse_entry_logs(text)
    logs = parse_exit_logs(text, logs)
    
    print(f"\nTotal Entries Found: {len(logs)}")
    
    logs = calculate_durations(logs)
    
    save_to_excel(logs, output_file)
    print(f"Processed {len(logs)} records. Data saved to {output_file}")

# Run the script
rtf_file = "ProlificLogSocratic1:30:25.rtf"  # Change this to your actual file path
output_excel = "prolific_log_timestamp_analysis.xlsx"  # Output file
process_rtf_logs(rtf_file, output_excel)

