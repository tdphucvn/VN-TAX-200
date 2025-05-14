import requests
import json
import os
import sys
import time
import subprocess
from bs4 import BeautifulSoup

BASE_URL="https://cafef.vn/du-lieu/"

def fetch_vietnam_tax_data():
    url = f"{BASE_URL}Ajax/CongTy/GetListNopNganSachGroup.ashx?type=vntax200&tab=top-200-doanh-nghiep"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching data: {e}")
        return None

if __name__ == "__main__":
    force_fetch = "--force-fetch" in sys.argv

    if not force_fetch and os.path.exists("top_200_companies.json"):
        print("'top_200_companies.json' already exists. Skipping fetch.")
        with open("top_200_companies.json", "r", encoding="utf-8") as file:
            data = json.load(file)
    else:
        data = fetch_vietnam_tax_data()
        if data:
            with open("top_200_companies.json", "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            print("Data has been saved to 'top_200_companies.json'.")

    if data:
        # Extract the list of companies
        companies = data.get("Data", []).get("Data", [])

        # Keep only 'CompanyName' and 'NopNganSach' fields
        filtered_companies = [
            {"Ranking": company.get("OrderNumber"),"CompanyName": company.get("ComapnyName"), "NopNganSach": company.get("NopNganSach"), "Link": company.get("Link"), "Industry": company.get("Industry"), "Type": company.get("Type")}
            for company in companies
        ]

        # Save the final list to a new JSON file
        with open("filtered_companies.json", "w", encoding="utf-8") as file:
            json.dump(filtered_companies, file, ensure_ascii=False, indent=4)
        print("Filtered data has been saved to 'filtered_companies.json'.")

        fetched_companies_file = "fetched_companies.json"
        fetched_companies = set()

        # Load already fetched companies if the file exists
        if os.path.exists(fetched_companies_file):
            with open(fetched_companies_file, "r", encoding="utf-8") as file:
                fetched_companies = set(json.load(file))

        os.makedirs("company_html", exist_ok=True)  # Create folder if it doesn't exist

        start_time = time.time()
        for idx, company in enumerate(filtered_companies, start=1):
            if company["CompanyName"] in fetched_companies:
                print(f"Skipping already fetched company: {company['CompanyName']}")
                continue

            link = company.get("Link")
            if link:
                details_url = f"{BASE_URL}{link}"
                try:
                    response = requests.get(details_url, timeout=30)  # Set a timeout of 30 seconds
                    response.raise_for_status()
                    html_file_path = os.path.join("company_html", f"company_{idx}.html")
                    with open(html_file_path, "w", encoding="utf-8") as html_file:
                        html_file.write(response.text)
                    print(f"HTML for {company['CompanyName']} saved to {html_file_path}")

                    # Add company to fetched list only if fetch is successful
                    fetched_companies.add(company["CompanyName"])

                    # Save the updated fetched companies list
                    with open(fetched_companies_file, "w", encoding="utf-8") as file:
                        json.dump(list(fetched_companies), file, ensure_ascii=False, indent=4)

                except requests.exceptions.Timeout:
                    print(f"Request for {company['CompanyName']} timed out. Moving to the next company.")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to fetch details for {company['CompanyName']}: {e}")

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Fetching HTML for all companies completed in {elapsed_time:.2f} seconds.")

        # Run the JavaScript script.js file
        try:
            print("Running the JavaScript script to process HTML files...")
            subprocess.run(["node", "script.js"], check=True)
            print("JavaScript script executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while running the JavaScript script: {e}")

        # Merge filtered_companies.json and company_details.json
        try:
            with open("filtered_companies.json", "r", encoding="utf-8") as filtered_file:
                filtered_companies = json.load(filtered_file)

            with open("company_details.json", "r", encoding="utf-8") as details_file:
                company_details = json.load(details_file)

            # Create a dictionary for quick lookup of company details by ranking
            details_dict = {company["Ranking"]: company for company in company_details if "Ranking" in company}

            # Merge the data
            merged_data = []
            for company in filtered_companies:
                ranking = company.get("Ranking")
                if ranking in details_dict:
                    merged_company = {**company, **details_dict[ranking]}
                    merged_data.append(merged_company)
                else:
                    merged_data.append(company)  # Add the company even if no details are found

            # Modify merged data to remove 'Earnings' and add 'Full Earnings'
            for company in merged_data:
                earnings = company.pop("Earnings", [])  # Remove 'Earnings' field
                company["Full Earnings"] = len(earnings) == 4  # Add 'Full Earnings' as a boolean

            # Save the updated merged data to a new JSON file
            with open("merged_companies.json", "w", encoding="utf-8") as merged_file:
                json.dump(merged_data, merged_file, ensure_ascii=False, indent=4)

            print("Updated merged data has been saved to 'merged_companies.json'.")

            # Convert merged data to CSV
            try:
                import csv

                csv_file_path = "merged_companies.csv"
                with open(csv_file_path, "w", encoding="utf-8", newline="") as csv_file:
                    csv_writer = csv.writer(csv_file)

                    # Write header
                    if merged_data:
                        header = merged_data[0].keys()
                        csv_writer.writerow(header)

                    # Write rows
                    for company in merged_data:
                        csv_writer.writerow(company.values())

                print(f"Merged data has been saved to '{csv_file_path}'.")
            except Exception as e:
                print(f"An error occurred while converting JSON to CSV: {e}")

            # Convert merged data to Excel
            try:
                import pandas as pd

                excel_file_path = "merged_companies.xlsx"
                df = pd.DataFrame(merged_data)
                df.to_excel(excel_file_path, index=False, engine="openpyxl")

                print(f"Merged data has been saved to '{excel_file_path}'.")
            except Exception as e:
                print(f"An error occurred while converting JSON to Excel: {e}")

        except Exception as e:
            print(f"An error occurred while merging JSON files: {e}")