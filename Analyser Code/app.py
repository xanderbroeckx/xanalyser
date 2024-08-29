"""
Created on Sun Aug 25 10:07:16 2024

@author: xanderbroeckx
"""
#%%
import tabula;
import numpy as np;
import pandas as pd;
from flask import Flask, session, redirect, url_for, request, render_template;
import os

#%% Data extraction out of pdf file

def extract_financials(filepath):
    return tabula.read_pdf(filepath, pages='all', multiple_tables=True);
#%% create mar with all the financials of the current ficsal year and last fiscal year

def create_mar(tables, year):
    # Concatenate account numbers data into a single DataFrame using a list comprehension
    account_numbers = pd.concat([tables[i] for i in range(3, 10)], axis=0)

    # Remove unnecessary columns and rename columns
    account_numbers.drop(['Unnamed: 1', "Toel."], axis=1, inplace=True)
    account_numbers.columns = ["Description", "AccNr", "CFY", "LFY"]

    # Convert CFY and LFY columns to numeric format efficiently
    account_numbers['CFY'] = pd.to_numeric(account_numbers['CFY'].fillna(0).str.replace(".", "", regex=False), errors='coerce').fillna(0).astype(int)
    account_numbers['LFY'] = pd.to_numeric(account_numbers['LFY'].fillna(0).str.replace(".", "", regex=False), errors='coerce').fillna(0).astype(int)

    # Concatenate toelichting data into a single DataFrame
    toelichting_full = pd.concat([tables[x] for x in range(10, len(tables))], axis=0)
    
    # Clean up the toelichting DataFrame and rename columns
    toelichting = toelichting_full[['Unnamed: 0', 'Codes', 'Boekjaar', 'Vorig boekjaar']].copy()
    toelichting.columns = ["Description", "AccNr", "CFY", "LFY"]

    # Convert columns in toelichting to appropriate formats
    toelichting['AccNr'] = toelichting['AccNr'].astype(str).str.replace(".0", "", regex=False)
    toelichting['CFY'] = pd.to_numeric(toelichting.CFY.fillna(0).astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).replace("XXXXXXXXXX", "0"), errors='coerce').fillna(0)
    toelichting['LFY'] = pd.to_numeric(toelichting.LFY.fillna(0).astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors='coerce').fillna(0)


    # Merge the account_numbers and toelichting DataFrames
    combined_data = pd.concat([account_numbers, toelichting], axis=0)

    # Create dictionaries for description and amounts based on AccNr
    mar_desc = combined_data.set_index('AccNr')['Description'].to_dict()
    mar_amount = combined_data.set_index('AccNr')[year].to_dict()

    # Fill missing descriptions using adjacent descriptions
    for key, value in mar_desc.items():
        if value == 0:
            index = combined_data.index.get_loc(key)
            mar_desc[key] = f"{combined_data.loc[index-1, 'Description']} {combined_data.loc[index+1, 'Description']}"

    # Construct the final mar dictionary
    mar = {key: {'description': mar_desc[key], 'amount': mar_amount[key]} for key in mar_amount if key in mar_desc}
    
    required_mar = ['9125','9145','9146','9126','9134','9150'];
                  
    for key in required_mar:
        mar.setdefault(key,0)
    
    return mar

#%%

def KFI(financials):
    
    KFI = {
        'Turnover' : financials['70']['amount'],
        'EBIT' : financials['9901']['amount'],
        'EBITDA' : financials['9901']['amount'] + financials['630']['amount'] + financials['631/4']['amount'] + financials['635/8']['amount'],
        'Pre Tax Result' : financials['9903']['amount'],
        'Net Result' : financials['9904']['amount'],
        'Net Financial Debt': financials['170/4']['amount']-financials['170']['amount'] - (financials['50/53']['amount'] + financials['54/58']['amount'])
        };
    
    return KFI;
#%%

def cashflows(pdf_file):
    financials_LFY = create_mar(pdf_file,year = 'LFY');
    financials_CFY = create_mar(pdf_file,year = 'CFY');
    
    
#%%    
    
def ratios(financials):
    
    
    #liquidity
    ratios = {
        
            #Liquidity
            'Current Ratio' : (financials['29/58']['amount'] + financials['29']['amount'])/ \
            (financials['42/48']['amount'] + financials['492/3']['amount']),
            
            'Quick Ratio' : (financials['40/41']['amount'] + financials['50/53']['amount']+ financials['54/58']['amount'] )/\
            (financials['42/48']['amount']),
            
            'Amount of days inventory' : financials['3']['amount']/((financials['60/66A']['amount']-financials['66A']['amount']-financials['71']['amount']-\
                                                 financials['72']['amount']-financials['740']['amount']-financials['9125']['amount'])/365),
            
            'Inventory Turnover' : 365/(financials['3']['amount']/((financials['60/66A']['amount']-financials['66A']['amount']-financials['71']['amount']-\
                                                 financials['72']['amount']-financials['740']['amount']-financials['9125']['amount'])/365)),
            
            'Amount of days client credit': (financials['40']['amount'] + financials['9150']['amount']) / \
                ((financials['70']['amount']+financials['74']['amount']-financials['740']['amount']+financials['9146']['amount'])/365),
            
            'Amount of days supplier credit': (financials['44']['amount'])/((financials['600/8']['amount'] + financials['61']['amount']+financials['9145']['amount'])/365),
            
            #Sovlency
            'General debt level %' : (financials['16']['amount'] +financials['17/49']['amount'])/financials['10/49']['amount']*100,
            
            'Financial Independence %' : financials['10/15']['amount']/financials['10/49']['amount']*100,
    
            'Coverage of financial costs by net result' : (financials['9904']['amount'] + financials['9134']['amount'] + financials['650']['amount'] + \
                                      financials['653']['amount'] - financials['9126']['amount'] )/ \
                                     (financials['650']['amount'] +financials['653']['amount'] - financials['9126']['amount']) ,
            
            #profitability
            'Gross Margin %' : (financials['9901']['amount'] - (financials['76A']['amount']-\
                         financials['66A']['amount']) + financials['630']['amount']+\
                         financials['631/4']['amount'] + financials['635/8']['amount'])/ \
                        (financials['70']['amount'] + financials['74']['amount'] - financials['740']['amount'])*100,
            
            'Net Margin %' : (financials['9901']['amount'] + financials['76A']['amount'] - financials['66A']['amount'] + financials['9125']['amount']) / \
                     (financials['70']['amount']+ financials['74']['amount'] -financials['740']['amount'])*100,
                     
            'Gross Financial Debt/EBITDA': (financials['170/4']['amount']-financials['170']['amount'])/\
                (financials['9901']['amount'] + financials['630']['amount'] + financials['631/4']['amount'] + financials['635/8']['amount']),
            
            'Net Financial Debt/EBITDA': (financials['170/4']['amount']-financials['170']['amount'] - (financials['50/53']['amount'] + financials['54/58']['amount']))/\
                (financials['9901']['amount'] + financials['630']['amount'] + financials['631/4']['amount'] + financials['635/8']['amount']),
            
            'Debt Service Coverage Ratio': (financials['9901']['amount'] + financials['630']['amount'] + financials['631/4']['amount'] + financials['635/8']['amount'])/\
                (financials['42']['amount']+financials['65']['amount'])
        };
    
    for key in ratios:
        ratios[key] = round(ratios[key],2);
        
    return ratios;    

#%%
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['input_value'] = request.form['input_value']
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
        
        # Process the file
        tables = extract_financials(filepath)
        financials = create_mar(tables, 'CFY')
        
        kfi = KFI(financials)
        kfi = {name: "{:,}".format(amount) for name, amount in kfi.items()}
        kfi_df = pd.DataFrame.from_dict(kfi, orient='index')
        
        ratio = ratios(financials)
        ratio_df = pd.DataFrame.from_dict(ratio, orient='index')
        
        # Convert DataFrames to HTML and store in session
        session['table1'] = kfi_df.to_html(classes='table table-striped', index=True, header=False)
        session['table2'] = ratio_df.to_html(classes='table table-striped', index=True, header=False)
        session['processed'] = True  # Set flag indicating data has been processed
        
        # Redirect to results page
        return redirect(url_for('result'))

@app.route('/result')
def result():
    # Check if the processed data is in the session
    if not session.get('processed', False):
        # Redirect back to upload page if no processed data in session
        return redirect(url_for('index'))
    
    table1 = session.get('table1', 'No data available')
    table2 = session.get('table2', 'No data available')
    
    return render_template('result.html', table1=table1, table2=table2)

if __name__ == '__main__':
    app.run(debug=True)





