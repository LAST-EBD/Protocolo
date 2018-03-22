
import os, re, time, tarfile, shutil
from __future__ import print_function
#from Protocolo import Landsat

usgs_OLD_id = None
usgs_NEW_id = None

def rename(ruta):

    '''Esta funcion hace el rename de escenas en una carpeta (por defecto 'C:\Protocolo\ori'), desde su nomenclatura en formato USGS 
    al formato YearMonthDaySatPath_Row. Funciona para Landsat 5-8. Si hubiera algun problema como posibles escenas duplicadas, 
    imprime la escena que da error y pasa a la siguiente. Las escenas que va renombrando correctamente son impresas en tambien en pantalla
                    LC08_L1TP_202034_20180127_20180207_01_T1 --->   20180127l8oli202_34
    '''
    print('Comenzando Rename')
    sats = {'LC8': 'l8oli', 'LE7': 'l7etm', 'LT5': 'l5tm'}
    
    for sc in os.listdir(ruta):
        
        if os.path.isdir(os.path.join(ruta, sc)):
            ruta_escena = os.path.join(ruta, sc)
        #Buscamos el MTL para obtener el nombre antiguo
        for i in os.listdir(ruta_escena):
            if i.endswith('MTL.txt'):
                mtl = os.path.join(ruta_escena,i)
                arc = open(mtl,'r')
                for i in arc:
                    if 'LANDSAT_SCENE_ID' in i:
                        global usgs_OLD_id 
                        usgs_OLD_id = i[-23:-2] #este es el antiguo nombre de Landsat
                    elif 'LANDSAT_PRODUCT_ID' in i:
                        global usgs_NEW_id 
                        usgs_NEW_id= i.split('=')[-1][2:-2]
                    
                            
                            
                #A VER SI SE PUEDE INCLUIR EL RENAME DE LAS BANDAS Y DEL MTL AQUI DENTRO
                arc.seek(0)
                lineas = arc.readlines()
                
                for n, e in enumerate(lineas):

                    if usgs_NEW_id in e and not "LANDSAT_PRODUCT_ID" in e:
                        lineas[n] = lineas[n].replace(usgs_NEW_id, usgs_OLD_id)
                
                for n, e in enumerate(lineas):
                    
                    if 'FILE_NAME_BAND_QUALITY' in e:
                        ix = n
                

                    else: continue
                    
                arc.close()

                print('Escena:', sc, 'Indice Quality band:', ix)
                
                if not 'LC08' in sc:
                    print('Eliminando BQA de', sc)
                    lineas.pop(ix)
                else:
                    print('Escena', sc)
                    
                f = open(mtl, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()                
                #YA ESTARIAN CAMBIADOS LOS NOMBRES EN EL MTL, AHORA HAY QUE CAMBIAR LOS NOMBRES DE LAS BANDAS
            
                print('OLD_id:', usgs_OLD_id, 'desde Rename')


                fecha=time.strftime("%d-%m-%Y")
                raiz = os.path.split(ruta_escena)[0]
                escena = usgs_OLD_id
                #nescena = path
                #print('LA ESCENA A RENOMBRAR ES', ruta_escena)
                sat = escena[:3]
                path =  escena[3:6]
                row = escena[7:9]
                fecha = time.strptime(escena[9:13] + " " + escena[13:16], '%Y %j')
                year = str(fecha.tm_year)
                month = str(fecha.tm_mon)
                if len(month) == 1:
                    month = '0' + month
                day = str(fecha.tm_mday)
                if len(day) == 1:
                    day = '0' + day

                outname = os.path.join(raiz, year +  month  + day + sats[sat] + path + "_" + row) #raiz, year +  month  + day
                print(outname)

                try:

                    #os.mkdir(outname)
                    #return outname
                    os.rename(ruta_escena, outname)
                    print('Escena', ruta_escena, 'renombrada a', outname)

                except Exception as e:
                    print(e, ruta_escena)
                    
                
        
def untar(ruta):

    '''Esta funcion realiza la descompresion y el borrado de los tar.bz originales. Descomprime los ficheros en una carpeta con el nombre
    en formato yearmonthdaysatpath_row que crea llamando a la funcion rename(), una vez descomprida la escena llama a la clase Landsat()
    y ejecuta el Protocolo para la correccion radiometrica'''
    
    print('empezando Untar')
    
    for i in os.listdir(ruta):

        if i.endswith('tar.gz'):
            
            fname = os.path.join(ruta, i)
            nfname = fname[:-7]
            print(fname, nfname)
        
        elif i.endswith('.tar'):
            
            fname = os.path.join(ruta, i)
            nfname = fname[:-5]
            #print(fname, nfname)
            
        else: continue
            
        try:

            tar = tarfile.open(fname) 

            #print('++++++++++++++++++++++++++++++')

            #nfname = os.path.join(os.path.split(fname)[0], nfname)
            
            os.mkdir(nfname)
            os.chdir(nfname)
            tar.extractall()
            
            #print(i, 'descomprimido')
            #print('++++++++++++++++++++++++++++++')

            tar.close()
            os.remove(fname)
            tar.close()
            os.chdir(r'C:\Protocolo')
            #rename(nfname)
            
                #Ahora hacermos el rename con la nueva nomenclatura!
                #nfname_ren = rename(nfname)
                

        except Exception as e:
            print(e, i)
            continue
            
            
def rename_bands(ruta):
    
    for sc in os.listdir(ruta):
        
        print('\nNEW IMAGE:', sc)
        if os.path.isdir(os.path.join(ruta, sc)):
            ruta_escena = os.path.join(ruta, sc)
        
        for i in os.listdir(ruta_escena):

            #print(i)

            if 'MTL' in i:
                #print(i)
                mtl = os.path.join(ruta_escena,i)
                print('MTL:', mtl, '\n')

                arc = open(mtl,'r')
                for i in arc:
                    if 'LANDSAT_SCENE_ID' in i:
                        usgs_OLD_id = i[-23:-2] #este es el antiguo nombre de Landsat
                    elif 'LANDSAT_PRODUCT_ID' in i:
                         usgs_NEW_id = i.split('=')[-1][2:-2]

                arc.close()
                print('DESDE RENAME BANDAS UGSGS IDS', usgs_NEW_id, usgs_OLD_id, '\n')
                
            #else: continue
        
        for ii in os.listdir(ruta_escena):
            
            #print('II:', ii)
            #print(usgs_NEW_id, usgs_OLD_id, 'Desde Rename de Bandas')

            nname = os.path.join(ruta_escena, ii.replace(usgs_NEW_id, usgs_OLD_id))
            oname = os.path.join(ruta_escena, ii)

            os.rename(oname, nname)
            #print('II:', oname, '--->', nname, '\n')            
        
        
        if os.path.exists(os.path.join(ruta_escena, 'gap_mask')):
            ruta_gapmask = os.path.join(ruta_escena, 'gap_mask')
            print('\nVAMOS A RENOMBRAR LAS GAPMASK', 'gap:', ruta_gapmask, 'oldID:', usgs_OLD_id, 'NewID:', usgs_NEW_id, '\n')
            rename_gapmask(ruta_gapmask, usgs_OLD_id, usgs_NEW_id)
            
        #del_bqa(ruta_escena)
            
            
def rename_gapmask(ruta_gapmask, old_id, new_id):
    
    for i in os.listdir(ruta_gapmask):
        
        nname = os.path.join(ruta_gapmask, i.replace(usgs_NEW_id, usgs_OLD_id))
        oname = os.path.join(ruta_gapmask, i)
        
        os.rename(oname, nname)
        
def del_bqa(ruta):
    
    print('In del_bqa')
    
        
    for sc in os.listdir(ruta):
        
        if not 'LC08' in sc:

            if os.path.isdir(os.path.join(ruta, sc)):
                ruta_escena = os.path.join(ruta, sc)

            #print('Eliminando BQA de', ruta_escena)
            for i in os.listdir(ruta_escena):
                if i.endswith('BQA.TIF'):
                    bqa = os.path.join(ruta_escena, i)

                    os.remove(bqa)
        else:
            print('L8 is fine')
           
            
            
#path = os.getcwd() Se podria hacer en el directorio que se quisiera
if __name__ == "__main__":
    ruta = r'C:\Protocolo'
    untar(ruta)
    rename(ruta)
    rename_bands(ruta)
    del_bqa(ruta)
    #Llamamos al Protocolo para todas las escenas ya descomprimidas de la carpeta ori
    for sc in os.listdir(ruta):
        
        if os.path.isdir(os.path.join(ruta, sc)):
        
            if 'l7etm' in sc and sc > '20030714':
                print('Landsat 7', sc,  'lista para aplicar el gapfill')

            else:
                ruta_escena = os.path.join(ruta, sc)
                print('ESCENA A PROCESAR:', sc)
                #MiEscena = Landsat(ruta_escena)
        
print('zACABO')