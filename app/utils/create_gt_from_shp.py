import datetime
import csv

import numpy as np
import geopandas as gpd
from geopy.distance import distance

from graph_tool.all import Graph, find_vertex, label_components

def progressbar(current_value,total_value,step=5,text='',progressSymbol='=',remainingSymbol=' ',currentSymbol=''):
    assert (100%step) == 0
    percentage = current_value / total_value * 100
    progress = int(percentage/step)
    remain = int(100/step-progress)
    if len(currentSymbol)>0:
        idx = current_value % len(currentSymbol)
        current = currentSymbol[idx]
    else:
        current = ''

    if percentage < 100:
        print("[{progress}{current}{remain}] {perc:5.1f}% {text}".format(progress=progressSymbol*progress,current=current,remain=remainingSymbol*(remain-len(current)),perc=percentage,text=text),
                                                    end="\r",flush=True)
    else:
        print("[{progress}{remain}] {perc:5.1f}% {text}".format(progress="="*progress,remain=" "*remain,perc=percentage,text=text),
                                                        end="\n",flush=True)


def lines_length(series):
    """Calculate lengths of geopandas series of lines in meters
    Args:
        series: a geopandas series of LineString objects with WGS 84 coordinates

    Returns:
        Series of lengths of lines in meters
    """
    return series.apply(line_length)


def line_length(line):
    """Calculate length of a line in meters, given in geographic coordinates.
    Args:
        line: a shapely LineString object with WGS 84 coordinates

    Returns:
        Length of line in meters

    Source:
        https://gis.stackexchange.com/a/115285
    """
    # Swap shapely (lonlat) to geopy (latlon) points
    latlon = lambda lonlat: (lonlat[1], lonlat[0])
    total_length = sum(distance(latlon(a), latlon(b)).meters
                       for (a, b) in pairs(line.coords))
    return total_length


def pairs(lst):
    """Iterate over a list in overlapping pairs without wrap-around.

    Args:
        lst: an iterable/list

    Returns:
        Yields a pair of consecutive elements (lst[k], lst[k+1]) of lst. Last
        call yields the last two elements.

    Example:
        lst = [4, 7, 11, 2]
        pairs(lst) yields (4, 7), (7, 11), (11, 2)

    Source:
        https://stackoverflow.com/questions/1257413/1257446#1257446
    """
    i = iter(lst)
    prev = next(i)
    for item in i:
        yield prev, item
        prev = item


def create_land_graph(shp_path):
    print("reading the file..")
    streets = gpd.read_file(shp_path)

    print("adapting to our needs..")
    lunghezza = lines_length(streets['geometry'])

    list_of_Codice_Pon_flat = ["MELONI"]
    # L'elenco di questi ponti è preso da https://www.comune.venezia.it/it/content/venezia-accessibile-itinerari-senza-barriere
    list_of_Codice_Pon_gradino_agevolato = ["PAGLIA", "SECHER", "PIERO", "RASPI", "GUGLIE", "PAPADO"]
    list_of_Codice_Pon_gradino_agevolato_con_accomp = ["FELICE"]
    list_of_Codice_Pon_rampa_fissa = ["QUINTA", "PALUDO"]
    list_of_Codice_Pon_rampa_provvisoria_feb_nov = ["VIN"]
    list_of_Codice_Pon_rampa_provvisoria_set_giu = ["MOLIN", "SALUTE", "CABALA", "INCURA", "CALCINA", "LUNGO"]
    list_of_Codice_Pon_rampa_provvisoria_mag_nov = ["VENETA"]

    ponte = []
    accessible = []
    for bridge in streets["Codice_Pon"]:
        if bridge:
            if bridge in list_of_Codice_Pon_flat:
                ponte.append(0)
                accessible.append(1)
            elif bridge in list_of_Codice_Pon_gradino_agevolato:
                ponte.append(1)
                accessible.append(2)
            elif bridge in list_of_Codice_Pon_gradino_agevolato_con_accomp:
                ponte.append(1)
                accessible.append(3)
            elif bridge in list_of_Codice_Pon_rampa_fissa:
                ponte.append(1)
                accessible.append(4)
            elif bridge in list_of_Codice_Pon_rampa_provvisoria_feb_nov:
                ponte.append(1)
                accessible.append(5)
            elif bridge in list_of_Codice_Pon_rampa_provvisoria_set_giu:
                ponte.append(1)
                accessible.append(6)
            elif bridge in list_of_Codice_Pon_rampa_provvisoria_mag_nov:
                ponte.append(1)
                accessible.append(7)
            else:
                ponte.append(1)
                accessible.append(0)
        else:
            ponte.append(0)
            accessible.append(1)

    print("creating a new dataframe only with the data we need..")
    # crea nuovo dataframe con solo colonne interessanti
    # pdb.set_trace()
    total = gpd.GeoDataFrame(data=zip(lunghezza, ponte, accessible,
                                      streets["geometry"], streets['V4W_ID'], streets['VEL_MAX'],
                                      streets['max_tide'], streets['min_tide'], streets['avg_tide'], streets['med_tide'],
                                      streets['Pass_cmZPS'], streets['Pass_altez']),
                             columns=["length", "ponte", "accessible",
                                      "geometry", "street_id",
                                      "vel_max", "max_tide", "min_tide", "avg_tide", "med_tide",
                                      "pas_cm_zps", "pas_height"])

    today = datetime.datetime.today().strftime('%d%m')

    new_shp_name = f"{shp_path[:-4]}_{today}.shp"
    print(f"New file will be {new_shp_name}")  # salva nuovo dataframe in shp
    
    return total, new_shp_name


def create_water_graph(shp_path):
    zucchetta_path = "Final Ponti Data CSV.csv"
    ponti = []

    print("\n\n\n\n\n*****\nWARNING\nCONTROLLA I PONTI! DA ZUCCHETTA A COMUNE\n*****\n\n\n\n\n")
    with open(zucchetta_path, 'r', encoding='latin') as csvfile:
        reader = csv.reader(csvfile)
        first_row = True
        for row in reader:
            if first_row:
                col_num_as_list = [i for i in range(len(row)) if row[i] == 'Minimum Height (m)']
                first_row = False
                col_num = col_num_as_list[0]
            elif row[0]:
                ponti.append({'altezza':row[col_num], 'bridge_num_zucchetta':row[0], 'nome':row[1]})
    print("reading the file..")
    shp_gpd = gpd.read_file(shp_path)

    print("adapting to our needs..")
    lunghezza = lines_length(shp_gpd['geometry'])
    solo_remi=[1 if i=='Rio Blu' else 0 for i in shp_gpd['BARCHE_A_R']]
    # normativa: to be done
    # c'è anche la stazza, ma per il momento non ci interessa (10t)
    vel_max=shp_gpd['VEL_MAX'][:]
    vel_max_mp=shp_gpd['VEL_MAX_MP'][:]
    larghezza=shp_gpd['LARGHEZZA_']
    senso_unico=shp_gpd['ONEWAY'][:]
    orario_senso_start=gpd.GeoSeries(np.zeros([larghezza.size], dtype=np.int8))
    orario_senso_end=gpd.GeoSeries(np.ones([larghezza.size], dtype=np.int8)*24)
    orario_chiuso_start=gpd.GeoSeries(np.ones([larghezza.size], dtype=np.int8)*24)
    orario_chiuso_end=gpd.GeoSeries(np.ones([larghezza.size], dtype=np.int8)*24)
    altezza=np.double(np.ones_like(solo_remi))*1000

    lista_sensi_inversi=["DE SAN LUCA - ROSSINI", "DE PALAZZO - CANONICA", "DE LA FAVA","DE LA PIETA'  - SANT'ANTONIN","DE SAN GIUSEPPE", "DE LA TETA - SAN GIOVANNI LATERANO RAMO BASSO", "DE SAN GIACOMO DALL'ORIO","DE SAN VIO"]
    lista_limiti_sette=["GRANDE","DE CANNAREGIO"]

    lista_no_info_per_non_dimenticare=["DE LE GALEAZZE", "SCUOLA GABELLI","DE LA VERONA - MENUO" ]
    lista_limiti_laguna=["DE LA RANA", "MOLO B", "DI CAMPALTO","COA DI LATTE","MORTO - MAZZORBO","CARBONERA","ALTINO","MONTIRON","DE SANT'ANTONIO","DEL COLPO", "DI BOSSOLARO", "LA ROTTA","CAMPANA", "BOMBAE", "PORTOSECCO","DE LA CAVA","CODA REZIOL"]
    vel_laguna=10
    lista_limiti_centro=["SCUOLA GABELLI","A. CANAL","DE LA SACA DE LA MISERICORDIA","ARSENAL VECHIO"] # in realtà sono quasi tutti al lido
    lista_divieti_0_24 = ["ARSENAL VECHIO"]################## caso particolare, gli altri hanno il divieto di transito nella colonna giusta!
    # canali con limite per canoe e simili dalle 8 alle 15 lunedì-venerdì e dalle 8 alle 13 il sabato
    lista_no_remetti = ["Canal Grande", "Cannaregio", "Giardini", "Greci - San Lorenzo", "- Santa Giustina - Sant’Antonin – Pietà", "Noale", "Novo", "Ca’ Foscari", "Santi Apostoli - Gesuiti"] # nomi da correggere
    vel_centro=5
    ponte_codes_list=[]
    epsilon=0.001
    for index,canal in shp_gpd.iterrows():

        print(canal['TC_DENOM'])
        if canal['DIVIETO_TR']:
            if 'art. 8' in canal['DIVIETO_TR']:
                print('divieto transito imbarcazioni a motore, esclusi concessionari spazi acquei e unità di enti e aziende pubbliche')
                orario_chiuso_start[index]=0
        if canal['DIVdiporto']:    
            print(canal['DIVdiporto'])
            orario_chiuso_start[index]=8
            orario_chiuso_end[index]=12
            
        if canal['VEL_MAX']==0:
            print(' has max vel=0')
            if canal['TC_DENOM'] in lista_limiti_laguna:
                vel_max[index]=vel_laguna
            if canal['TC_DENOM'] in lista_limiti_centro:
                vel_max[index]=vel_centro
            if not canal['TC_DENOM']:
                print("changed max speed in none canal")
                vel_max[index]=vel_laguna
        if canal['VEL_MAX_MP']==0:
           # print(canal['TC_DENOM'], ' has max vel=0')
            if canal['TC_DENOM'] in lista_limiti_laguna:
                vel_max_mp[index]=vel_laguna
            if canal['TC_DENOM'] in lista_limiti_centro:
                vel_max_mp[index]=vel_centro
            if not canal['TC_DENOM']:
                vel_max_mp[index]=vel_laguna
                
        if solo_remi[index]==1:
            #print('era un rio blu')
            vel_max_mp[index]=vel_centro
            vel_max[index]=vel_centro
    
        if not np.isnan(canal['Numero_Zuc']): # != "None": #is not None:
            print('trovato ponte ', canal['Nome_Ponte'])
            for ponte in ponti:

                if np.abs(float(ponte['bridge_num_zucchetta'])-float(canal['Numero_Zuc']))<epsilon:
                    ponte_codes_list.append(canal['Numero_Zuc'])
                    altezza[index]=ponte['altezza']
                    print("il ponte {} e alto {}".format(ponte['nome'], ponte['altezza']))
                    break
        if canal['TC_DENOM']=="DEI FUSERI":
            print('aggiungo senso unico al rio dei fuseri')
            senso_unico[index]=1
        if canal['TC_DENOM']=="DEI VETRAI":
            print('aggiungo senso unico al rio dei vetrai')
            senso_unico[index]=1
        if canal['TC_DENOM']=="DE CA' FOSCARI":
            print('aggiungo senso unico al rio di ca foscari')
            senso_unico[index]=1
        if senso_unico[index] is not None:

            if canal['TC_DENOM'] in lista_sensi_inversi:
                print('cambiato verso di ', canal['TC_DENOM'])
                senso_unico[index]=-1
            else:
                senso_unico[index]=1
            if canal['TC_DENOM'] in ["DE CA' FOSCARI", "NOVO"]:
                orario_senso_start[index]=0
                orario_senso_end[index]=12
            if canal['TC_DENOM']=="DEI VETRAI":
                orario_senso_start[index]=8 #solo feriali
                orario_senso_end[index]=14

        if canal['TC_DENOM'] in lista_limiti_sette:
            print('cambio limite di velocita nel ', canal['TC_DENOM'])
            vel_max[index]=7
            vel_max_mp[index]=11
        if canal['TC_DENOM']=="SAN CRISTOFORO":
            print('modifico limite di velocita canale di san cristoforo')
            vel_max[index]=11

    assert(len(ponti)==len(ponte_codes_list),'diversi ponti tra shp e csv')

    #da aggiungere a total: h_closed_start, h_closed_end
    total = gpd.GeoDataFrame(data = zip(lunghezza, vel_max, vel_max_mp, solo_remi, larghezza, altezza, senso_unico, orario_senso_start,orario_senso_end, orario_chiuso_start, orario_chiuso_end, shp_gpd["TC_DENOM"],shp_gpd["geometry"]),
    columns = ["length","vel_max", "vel_max_mp", "solo_remi", "larghezza", "altezza", "senso_unico", "h_su_start","h_su_end", "dt_start", "dt_end", "nome","geometry"])

    today = datetime.datetime.today().strftime ('%d%m')
    new_shp_name = f"{shp_path[:-4]}_{today}.shp"
    
    print(f"New file will be {new_shp_name}")  # salva nuovo dataframe in shp
    
    return total, new_shp_name


def retrieve_attribute_type(attribute):
    dequa_types = {
        # grafo di terra
        'length': 'float',
        'ponte': 'int',
        'accessible': 'int',
        'street_id': 'float',
        'vel_max': 'float',
        'max_tide': 'float',
        'min_tide': 'float',
        'avg_tide': 'float',
        'med_tide': 'float',
        'pas_cm_zps': 'float',
        'pas_height': 'float',
        'geometry': 'object',
        # grafo di acqua
        'vel_max_mp': 'float',
        'solo_remi': 'int',
        'larghezza': 'float',
        'altezza': 'float',
        'senso_unic': 'float',
        'h_su_start': 'int',
        'h_su_end': 'int',
        'dt_start': 'int',
        'dt_end': 'int',
        'nome': 'string',
        # quale la differenza con `senso_unic` ?
        'one_way': 'int', # it can have 0, 1 and -1
        # non sono sicuro, forse per descrizione proprio semantica?
        'DESCR': 'string',
        'CLASS': 'int',
        # moto ondoso (valori manuali)
        'motoondoso': 'int', 
        # profondita' dei canali (presi dalle batimetriche)
        'prof_min': 'float',
        'prof_max': 'float',
        'prof_mean': 'float',
    }
    if attribute in dequa_types.keys():
        return dequa_types[attribute]
    else:
        return "No type detected"
    

def get_vertices_from_geometry(g, geometry):
    coord_source = geometry.coords[0]
    coord_target = geometry.coords[-1]
    latlon = g.vertex_properties['latlon']
    source = find_vertex(g, latlon, coord_source)
    if not source:
        source = g.add_vertex()
        g.vp.latlon[source] = coord_source
    else:
        source = source[0]
    target = find_vertex(g, latlon, coord_target)
    if not target:
        target = g.add_vertex()
        g.vp.latlon[target] = coord_target
    else:
        target = target[0]

    return source, target


def add_properties_to_edge(g, edge, properties):
    for property in properties.keys():
        g.ep[property][edge] = properties[property]
    return

def geodf2gt(geodf):
    print("Reading the file...")
    df = geodf

    if 'solo_remi' in df.columns:
        water_graph = True
        print("It is a water graph")
    else:
        water_graph = False
        print("It is a street graph")

    print("The file has {} edges.".format(len(df)))
    print("Each edge has these attributes: {}".format([col for col in df.columns]))

    print("Creating the graph...")
    g = Graph(directed=False)
    if water_graph:
        g.set_directed(True)

    # Add attributes as edge properties
    for col in df.columns:
        eprop = g.new_edge_property(retrieve_attribute_type(col))
        g.edge_properties[col] = eprop

    # Add the coordinates as vertex property
    vprop = g.new_vertex_property("vector<float>")
    g.vertex_properties['latlon'] = vprop

    print("Adding vertices and edges...")
    # Start extracting the info iterating by all the rows
    for index, row in df.iterrows():
        source, target = get_vertices_from_geometry(g, row['geometry'])
        # if it is a water graph we check the direction
        if water_graph:
            if row['senso_unic'] == -1:
                # it is already correct
                edge = g.add_edge(source, target)
                edge2 = None
            elif row['senso_unic'] == 1:
                edge = g.add_edge(target, source)
                edge2 = None
            else:
                edge = g.add_edge(source, target)
                edge2 = g.add_edge(target, source)
        else:
            edge = g.add_edge(source, target)
            edge2 = None
        # add the properties to the edge
        for property in row.keys():
            txt = f"Updating prop {property} of edge {edge}"
            progressbar(index+1, len(df), text=txt)
            g.ep[property][edge] = row[property]
            if edge2:
                g.ep[property][edge2] = row[property]

    # add property component
    comp, hist = label_components(g)
    # starting from 1 to avoid confusion if more edges are added
    comp.a += 1
    g.vp.component = comp
    
    print("GRAPH PROPERTIES")
    print (g.list_properties())
    print("================")

    print("GRAPH ENTITY COUNT")
    print ("Vertices: {}".format(str(g.num_vertices())))
    print ("Edges: {}".format(str(g.num_edges())))
    print("================")

    return g