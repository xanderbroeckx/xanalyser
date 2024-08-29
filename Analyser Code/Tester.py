#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 25 10:07:16 2024

@author: xanderbroeckx
"""
#%%
import tabula
import numpy as np
import pandas as pd
import os
from pprint import pprint;
#%%
# name pdf file
filepath = '/Users/xanderbroeckx/Documents/Annual Accounts Project/AA 2023 DCM.pdf'
# get all the required tables 
#tables = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True)
#%%
def extract_financials(filepath):
    # Read all tables at once from the PDF file
    return tabula.read_pdf(filepath, pages='all', multiple_tables=True)

tables = extract_financials(filepath)
#%%
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

    return mar


mar = create_mar(tables, 'CFY')

def KFI(financials):
    
    KFI = {
        'Turnover' : financials['70']['amount'],
        'EBIT' : financials['9901']['amount'],
        'EBITDA' : financials['9901']['amount'] + financials['630']['amount'] + financials['631/4']['amount'] + financials['635/8']['amount'],
        'Pre Tax Result' : financials['9903']['amount'],
        'Net Result' : financials['9904']['amount']
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
        };
    
    for key in ratios:
        ratios[key] = round(ratios[key],2);
        
    return ratios;    

#%% Financials

def main():
    
    
    #pdf_file = import_file();
    tables = extract_financials(filepath);
    financials = create_mar(tables, 'CFY');
    
    print("Key Financial Information: \n");
    kfi = KFI(financials);
    pprint(kfi, depth = 1);
    
    print("\n Ratios: \n");
    ratio = ratios(financials);
    pprint(ratio, depth = 1);
    
    return financials;

financials = main();



#%%
# make one dataframe with balance sheet and p&l 
account_numbers = pd.DataFrame()
for i in range(3,10):
    account_numbers = pd.concat([account_numbers,tables[i]],axis = 0)

# remove last column                                 
account_numbers = account_numbers.drop(['Unnamed: 1', "Toel."]
                                       , axis = 1)
account_numbers.columns = ["Description", "AccNr","CFY", "LFY"]

#Conversion to numbers
CFY = account_numbers.CFY.copy()
CFY.fillna(value = 0, inplace = True)
CFY = np.array(CFY).reshape(-1,1).astype('str')
CFY = np.char.replace(CFY, ".", "").astype('int')

LFY = account_numbers.LFY.copy()
LFY.fillna(value = 0, inplace = True)
LFY = np.array(LFY).reshape(-1,1).astype('str')
LFY = np.char.replace(LFY, ".", "").astype('int')

account_numbers = account_numbers.drop(['CFY','LFY'], axis = 1)
account_numbers = np.concatenate([account_numbers, CFY, LFY], axis = 1)
account_numbers = pd.DataFrame(account_numbers)
account_numbers.columns = ["Description", "AccNr","CFY", "LFY"]
account_numbers.Description.fillna(value = 0, inplace = True)
#%%

toelichting_full = pd.DataFrame()
for x in range(10,len(tables)):
    toelichting_full = pd.concat([toelichting_full,tables[x]],axis = 0);
#%%    
toelichting = toelichting_full[['Unnamed: 0', 'Codes', 'Boekjaar', 'Vorig boekjaar']];
toelichting.columns = ["Description", "AccNr","CFY", "LFY"];

#%%
toelichting_AccNr = toelichting.AccNr.copy();
toelichting_AccNr = np.array(toelichting_AccNr).reshape(-1,1).astype('str');
toelichting_AccNr = np.char.replace(toelichting_AccNr, ".0", "");
#%%
toelichting_CFY = toelichting.CFY.copy();
toelichting_CFY.fillna(value = 0, inplace = True);
toelichting_CFY = np.array(toelichting_CFY).reshape(-1,1).astype('str');
toelichting_CFY = np.char.replace(toelichting_CFY, ["."], "");
toelichting_CFY = np.char.replace(toelichting_CFY, [","], ".");
toelichting_CFY = np.char.replace(toelichting_CFY, ["XXXXXXXXXX"], "0").astype('float');

#%%
toelichting_LFY = toelichting.LFY.copy();
toelichting_LFY.fillna(value = 0, inplace = True);
toelichting_LFY = np.array(toelichting_LFY).reshape(-1,1).astype('str');
toelichting_LFY = np.char.replace(toelichting_LFY, ".", "");
toelichting_LFY = np.char.replace(toelichting_LFY, [","], ".").astype('float');
#%%
toelichting = toelichting.drop(['AccNr','CFY','LFY'], axis = 1)
toelichting = np.concatenate([toelichting, toelichting_AccNr, toelichting_CFY, toelichting_LFY], axis = 1)
toelichting = pd.DataFrame(toelichting)
toelichting.columns = ["Description", "AccNr","CFY", "LFY"]  
#%%
account_numbers = pd.concat([account_numbers,toelichting],axis=0)

mar_desc = account_numbers.set_index('AccNr')['Description'].to_dict();

for key in mar_desc:
    if (mar_desc[key] == 0):
        index = pd.Index(account_numbers.AccNr).get_loc(key);
        mar_desc[key] = account_numbers.Description[index-1] + " " + account_numbers.Description[index+1];
        

#%%

#descriptions = account_numbers

# Create Dictionary which we will use
mar_desc = account_numbers.set_index('AccNr')['Description'].to_dict()

for key in mar_desc:
    if (mar_desc[key] == 0):
        index = pd.Index(account_numbers.AccNr).get_loc(key)
        mar_desc[key] = account_numbers.Description[index-1] + " " + account_numbers.Description[index+1]
        
mar = account_numbers.set_index('AccNr')['CFY'].to_dict()

#%% Ratios