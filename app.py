"""
Created on Sun Aug 25 10:07:16 2024

@author: xanderbroeckx
"""
#%%
#pip install tabula-py flask PyPDF2 pandas numpy

import tabula
import numpy as np;
import pandas as pd;
from flask import Flask, session, redirect, url_for, request, render_template;
import os
import PyPDF2

#%% Data extraction out of pdf file

def extract_financials(filepath):
    start_words = ['CONSO 3.1', 'VOL-kap 3.1', 'VKT-kap 3.1', 'MIC-kap 3.1','VOL-kap 3.1','VOL-inb 3.1', 'VKT-inb 3.1', 'MIC-inb 3.1']
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        # Loop through all pages and search for any word in start_words
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            # Check if any word from the list is present on the page
            for word in start_words:
                if word in text:
                    return tabula.read_pdf(filepath, pages=f"{page_num + 1}-{len(reader.pages)}", multiple_tables=True, silent = True)
        return None
    
#%% create mar with all the financials of the current ficsal year and last fiscal year

def create_mar(tables):
    # Concatenate account numbers data into a single DataFrame using a list comprehension
    account_numbers_full = pd.concat([tables[i] for i in range(0, len(tables))], axis=0)
    
    # Create a deep copy of the DataFrame to avoid SettingWithCopyWarning
    account_numbers = account_numbers_full[['Unnamed: 0', 'Codes', 'Boekjaar', 'Vorig boekjaar']].copy()

    # Remove unnecessary columns and rename columns
    account_numbers.columns = ["Description", "AccNr", "CFY", "LFY"]

    # Convert 'AccNr' column to string and replace ".0" 
    account_numbers.loc[:, 'AccNr'] = account_numbers['AccNr'].astype(str).str.replace(".0", "", regex=False)
    
    # Convert 'CFY' and 'LFY' columns to numeric format efficiently
    account_numbers.loc[:, 'CFY'] = pd.to_numeric(
        account_numbers['CFY'].fillna(0).astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .replace("XXXXXXXXXX", "0"), errors='coerce').fillna(0)

    account_numbers.loc[:, 'LFY'] = pd.to_numeric(
        account_numbers['LFY'].fillna(0).astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False), errors='coerce').fillna(0)

    # Create dictionaries for description and amounts based on 'AccNr'
    mar_desc = account_numbers.set_index('AccNr')['Description'].to_dict()
    mar_amount_CFY = account_numbers.set_index('AccNr')['CFY'].to_dict()
    mar_amount_LFY = account_numbers.set_index('AccNr')['LFY'].to_dict()

     # Ensure certain keys are present in the 'mar' dictionary
    required_mar = ['9125', '9145', '9146', '9126', '9134', '9150']
    required_mar_desc = ['Kapitaalsubsidies','Aan de vennootschap (aftrekbaar)','Door de vennootschap','Interestsubsidies','Belastingen op het resultaat van het boekjaar','Door de vennootschap geëndosseerde handelseffecten in omloop']
    for key in range(0,len(required_mar)):
        mar_amount_CFY.setdefault(str(required_mar[key]), 0)# Ensure the key is set as a string
        mar_amount_LFY.setdefault(str(required_mar[key]), 0)
        mar_desc.setdefault(str(required_mar[key]), required_mar_desc[key])

    # Fill missing descriptions using adjacent descriptions
    for key, value in mar_desc.items():
        if value == 0:
            index = account_numbers.index.get_loc(key)
            mar_desc[key] = f"{account_numbers.loc[index-1, 'Description']} {account_numbers.loc[index+1, 'Description']}"

    # Construct the final 'mar' dictionary
    mar = {key: {'description': mar_desc[key], 
                 'CFY': mar_amount_CFY[key], 
                 'LFY': mar_amount_LFY[key]} 
                 for key in mar_amount_CFY if key in mar_desc}

   

    return mar


#%%

def safe_divide(numerator, denominator):
        return numerator / denominator if denominator != 0 else 'Not Applicable'

def KFI(financials, years, option):
    # Initialize a dictionary to hold KFI values for each year
    kfi = {year: {} for year in years}

    # Define calculations for different KFIs
    if option == 'Full':
        calculations = {
            'Turnover': lambda year: financials['70'].get(year, 0),
            'EBIT': lambda year: financials['9901'].get(year, 0),
            'EBITDA': lambda year: financials['9901'].get(year, 0) + financials['630'].get(year, 0) + financials['631/4'].get(year, 0) + financials['635/8'].get(year, 0),
            'Pre Tax Result': lambda year: financials['9903'].get(year, 0),
            'Net Result': lambda year: financials['9904'].get(year, 0),
            'Net Financial Debt': lambda year: financials['170/4'].get(year, 0) - financials['170'].get(year, 0) - (financials['50/53'].get(year, 0) + financials['54/58'].get(year, 0)),
            'Gross Margin %': lambda year: safe_divide(
                financials['9901'].get(year, 0) - (financials['76A'].get(year, 0) - financials['66A'].get(year, 0)) + 
                financials['630'].get(year, 0) + financials['631/4'].get(year, 0) + financials['635/8'].get(year, 0),
                financials['70'].get(year, 0) + (financials['74'].get(year, 0) - financials['740'].get(year, 0))
            ) * 100,
            'Net Margin %': lambda year: safe_divide(
                financials['9901'].get(year, 0) + financials['76A'].get(year, 0) - financials['66A'].get(year, 0) + 
                financials['9125'].get(year, 0),
                financials['70'].get(year, 0) + (financials['74'].get(year, 0) - financials['740'].get(year, 0))
            ) * 100,
        }
    
    else:
        calculations = {
            'Gross Margin': lambda year: financials['9900'].get(year, 0),
            'EBIT': lambda year: financials['9901'].get(year, 0),
            'EBITDA': lambda year: financials['9901'].get(year, 0) + financials['630'].get(year, 0) + financials['631/4'].get(year, 0) + financials['635/8'].get(year, 0),
            'Pre Tax Result': lambda year: financials['9903'].get(year, 0),
            'Net Result': lambda year: financials['9904'].get(year, 0),
            'Net Financial Debt': lambda year: financials['170/4'].get(year, 0) - (financials['50/53'].get(year, 0) + financials['54/58'].get(year, 0)),
        }


    # Calculate KFI values for each year
    for year in years:
        for kfi_name, calc in calculations.items():
            if isinstance(calc(year),(int, float)):
                kfi[year][kfi_name] = round(calc(year), 2)

    # Convert KFI dictionary to a DataFrame
    df = pd.DataFrame({
        'CFY': [kfi['CFY'].get(kfi_name, 'N/A') for kfi_name in calculations],
        'LFY': [kfi['LFY'].get(kfi_name, 'N/A') for kfi_name in calculations]},
        index=calculations)

    return df
#%%
"""
def cashflows(financials):
    'Operational CF': financials[].get('CFY',0)

    
    
    return
"""  
#%%    
    
def ratios(financials, years, option):
    # Initialize a dictionary to hold the ratios for each calculation type
    ratios = {year: {} for year in years}

    # Define calculations for different ratios
    calculations = {
        'Current Ratio': lambda year: safe_divide(
            financials['29/58'].get(year, 0) - financials['29'].get(year, 0),
            financials['42/48'].get(year, 0) + financials['492/3'].get(year, 0)
        ),
        'Quick Ratio': lambda year: safe_divide(
            financials['40/41'].get(year, 0) + financials['50/53'].get(year, 0) + financials['54/58'].get(year, 0),
            financials['42/48'].get(year, 0)
        ),
        # Solvency Metrics
        'General debt level %': lambda year: safe_divide(
            financials['16'].get(year, 0) + financials['17/49'].get(year, 0),
            financials['10/49'].get(year, 0)
        ) * 100,
        'Financial Independence %': lambda year: safe_divide(
            financials['10/15'].get(year, 0),
            financials['10/49'].get(year, 0)
        ) * 100,
        'Coverage of financial costs by net result': lambda year: safe_divide(
            financials['9904'].get(year, 0) + financials['9134'].get(year, 0) + (financials['650'].get(year, 0) +
            financials['653'].get(year, 0) if option == 'Full' else financials['65'].get(year,0)) - financials['9126'].get(year, 0),
            (financials['650'].get(year, 0) + financials['653'].get(year, 0) if option == 'Full' else financials['65'].get(year,0)) - financials['9126'].get(year, 0)
        ),
        'DSCR': lambda year: safe_divide(
            financials['9901'].get(year, 0) + financials['630'].get(year, 0) + financials['631/4'].get(year, 0) + financials['635/8'].get(year, 0),
            financials['42'].get(year, 0) + (financials['650'].get(year, 0) if option == 'Full' else financials['65'].get(year, 0))
        ),
        'Gross Leverage Ratio': lambda year: safe_divide(
            financials['17'].get(year, 0) - (financials['170'].get(year, 0) if option == 'Full' else 0) + financials['42'].get(year, 0) + financials['43'].get(year, 0),
            financials['9901'].get(year, 0) + financials['630'].get(year, 0) + financials['631/4'].get(year, 0) + financials['635/8'].get(year, 0)
        ),
        'Net Leverage Ratio': lambda year: safe_divide(
            financials['17'].get(year, 0) - (financials['170'].get(year, 0) if option == 'Full' else 0) + financials['42'].get(year, 0) + financials['43'].get(year, 0) - (financials['50/53'].get(year, 0) + financials['54/58'].get(year, 0)),
            financials['9901'].get(year, 0) + financials['630'].get(year, 0) + financials['631/4'].get(year, 0) + financials['635/8'].get(year, 0)
        )
    }
    
    # Only add specific metrics if option == 'Full'
    if option == 'Full':
        calculations.update({
            'Amount of days inventory': lambda year: safe_divide(
                financials['3'].get(year, 0),
                (financials['60/66A'].get(year, 0) - financials['66A'].get(year, 0) - financials['71'].get(year, 0) + financials['72'].get(year, 0) - financials['740'].get(year, 0) - financials['9125'].get(year, 0)) / 365
            ),
            'Inventory Turnover': lambda year: safe_divide(
                financials['60/66A'].get(year, 0) - financials['66A'].get(year, 0) - financials['71'].get(year, 0) + financials['72'].get(year, 0) - financials['740'].get(year, 0) - financials['9125'].get(year, 0),
                financials['3'].get(year, 0)
            ),
            'Amount of days client credit': lambda year: safe_divide(
                financials['40'].get(year, 0) + financials['9150'].get(year, 0),
                (financials['70'].get(year, 0) + financials['74'].get(year, 0) - financials['740'].get(year, 0) + financials['9146'].get(year, 0)) / 365
            ),
            'Amount of days supplier credit': lambda year: safe_divide(
                financials['44'].get(year, 0),
                (financials['600/8'].get(year, 0) + financials['61'].get(year, 0) + financials['9145'].get(year, 0)) / 365
            )
        })

    # Calculate ratios for each year
    for year in years:
        for ratio, calc in calculations.items():
            if isinstance(calc(year),(int, float)):
                ratios[year][ratio] = round(calc(year), 2)

    # Combine results into a single DataFrame
    df = pd.DataFrame({
    'CFY': [ratios['CFY'].get(ratio, 'Not Applicable') for ratio in calculations],
    'LFY': [ratios['LFY'].get(ratio, 'Not Applicable') for ratio in calculations]}, 
            index=calculations)
    
    return df

def format_dataframe(df):
    # Define a function to format numbers with comma separators and rounding
    def format_number(x):
        try:
            return "{:,.2f}".format(x)  # Format with comma separators and 2 decimal places
        except (ValueError, TypeError):
            return x  # Return as-is if formatting fails

    # Apply the formatting function to each cell in the DataFrame
    formatted_df = df.applymap(format_number)

    return formatted_df

#%%
app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['input_value'] = request.form.get('input_value', '')
        session['option'] = request.form.get('option', '')
        return redirect(url_for('index'))
    return render_template('index.html', input_value=session.get('input_value', ''))

@app.route('/process_file', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return "No file part"
    
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file"
    
    if file and allowed_file(file.filename):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        option = request.form.get('option', '')
        if not option:
            return "No option selected"
        
        # Process the file
        tables = extract_financials(filepath)
        financials = create_mar(tables)
        
        kfi = format_dataframe(KFI(financials, ['CFY', 'LFY'], option = option))
        ratio = format_dataframe(ratios(financials, ['CFY', 'LFY'], option = option))
        
        # Convert DataFrames to HTML and store in session
        session['table1'] = kfi.to_html(classes='table table-striped', index=True, header=True)
        session['table2'] = ratio.to_html(classes='table table-striped', index=True, header=True)
        session['processed'] = True  # Set flag indicating data has been processed
        
        # Redirect to results page
        return redirect(url_for('result'))

@app.route('/result')
def result():
    if not session.get('processed', False):
        return redirect(url_for('index'))
    
    table1 = session.get('table1', 'No data available')
    table2 = session.get('table2', 'No data available')
    
    return render_template('result.html', table1=table1, table2=table2)

if __name__ == '__main__':
    app.run(debug=True)