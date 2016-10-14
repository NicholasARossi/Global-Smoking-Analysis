import pandas as pd
import numpy as np
import os
import vincent
import pycountry
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style('white')


def renaming_iso3(df):
    ### This function renames the countries in a way that vincent will understand
    countries = {}
    for country in pycountry.countries:
        countries[country.name] = country.alpha3

    for index, row in df.iterrows():
        row['Country'] = countries.get(row['Country'], 'Unknown code')
    return countries


def clean_data_frame(total,countries,key):
    ### This function cleans and generates a data frame that will fit well into the vincent map
    import json
    with open('world-countries.topo.json', 'r') as f:
        get_id = json.load(f)

    new_geoms = []
    for geom in get_id['objects']['world-countries']['geometries']:
        new_geoms.append(geom['id'])

    amounts = np.zeros((np.shape(new_geoms)[0]))
    j = 0
    amounts = [0] * len(new_geoms)

    for index, row in total.iterrows():

        if countries.get(row['Country'].replace(u'\xa0', u''), 'Unknown code') in new_geoms:
            amounts[new_geoms.index(countries.get(row['Country'].replace(u'\xa0', u''), 'Unknown code'))] = row[key]
        else:
            ### Print off un-recognized countries
            print(row['Country'])
    targets = np.where(np.array(amounts) == 0)[0]
    for target in sorted(targets, reverse=True):
        del new_geoms[target]
        del amounts[target]

    # ### hacky fix to get the USA to show up
    # if key=='Value':
    #     new_geoms.append(u'USA')
    #     amounts.append(17.2)

    map_data = pd.DataFrame({'iso3': new_geoms, key: amounts})
    return map_data

def map_generator(map_data,key,title):
    ### This function makes a colored map for the data given, white outlines for countries without data

    geo_data = [{'name': 'countries',
                 'url': 'world-countries.topo.json',
                 'feature': 'world-countries'},
                {'name': 'countries_outline',
                 'url': 'world-countries.topo.json',
                 'feature': 'world-countries'}
                ]

    mapx = vincent.Map(data=map_data, geo_data=geo_data, projection='mercator', scale=150,
                       data_bind=key, data_key='iso3',
                       map_key={'countries': 'id'}, brew='Purples')
    del mapx.marks[1].properties.update
    mapx.marks[1].properties.enter.stroke.value = '#000'
    mapx.legend(title=title)
    return mapx

if __name__ == '__main__':

    ### primary driver for generating the maps of interest

    ### step 1: import the data
    folder = 'WHO_data/'

    names = os.listdir(folder)

    ### just mac things:
    names.remove('.DS_Store')

    for g, name in enumerate(names):
        frame = pd.read_excel(folder + name)
        if g == 0:
            total_df = frame
        elif g > 0:
            total_df = pd.concat([frame, total_df])

    # total_df=total_df.set_index('Country')


    countries=renaming_iso3(total_df)

    ### step 3: generate map data
    map_data=clean_data_frame(total_df,countries,'Value')

    ### Cigarette per capita data
    frame = pd.read_excel('non_cigarette_data/CPC.xlsx')
    countries2 = renaming_iso3(frame)
    map_data2 = clean_data_frame(frame, countries2,'CPC')

    ### Population Data
    frame = pd.read_excel('non_cigarette_data/population.xlsx')
    countries3 = renaming_iso3(frame)
    map_data3 = clean_data_frame(frame, countries3,'Pop')


    ### Merging dataframes
    Final_frame=pd.merge(map_data, map_data2, on='iso3')
    Final_frame=pd.merge(Final_frame, map_data3, on='iso3')
    Final_frame['Cigs'] = (Final_frame['CPC']*(100.0/Final_frame['Value'])/365)
    titles=['Percent_Smokers','Cigarettes_Per_Smoker']
    keys=['Value','Cigs']
    Final_frame['ranks']=Final_frame.groupby(['iso3'])['Cigs'].rank(ascending=False)

    ## step 4: generate maps (one for each variable)
    for j in range(len(titles)):
        mapx=map_generator(Final_frame,keys[j],titles[j])
        ## step 5: save map
        mapx.to_json('vega'+str(j)+'.json', html_out=True, html_path=titles[j]+'.html')


    ### The following generates the static charts
    ### Top countries
    f,(ax1,ax2)=plt.subplots(1,2,figsize=(10, 4), dpi=200)
    ax1.set_axis_bgcolor('w')
    Final_frame.sort(['Value'])[-20:-1].plot(x="iso3", y="Value", kind='bar',ax=ax1,color='red')
    ax1.set_xlabel('Country')
    ax1.set_ylabel('% Smokers')
    ax1.legend([])
    ax2.set_axis_bgcolor('w')
    Final_frame.sort(['Cigs'])[-20:-1].plot(x="iso3", y="Cigs", kind='bar',ax=ax2,color='Purple')
    ax2.set_xlabel('Country')
    ax2.set_ylabel('# Cigarettes/Smoker/Day')
    ax2.legend([])


    plt.savefig('cig_subplots.png',bbox_inches='tight')

    ### Correlations
    f2,ax3 = plt.subplots(1,1)
    sns.regplot(x="Value", y="Cigs",data=Final_frame,color='#c44240')
    sns.set_style('white')
    plt.xlabel('% smokers')
    plt.title('Relationship between % population that smokes \n and how much they smoke')
    plt.ylabel('Number of Cigarettes Smoked per Day')
    plt.savefig('comparison.png')


