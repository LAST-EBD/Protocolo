######## PROTOCOLO AUTOMATICO PARA LA CORRECCION RADIOMETRICA DE ESCENAS LANDSAT 8 #######
######                                                                              ######
####                        Autor: Diego Garcia Diaz                                  ####
###                      email: digd.geografo@gmail.com                                ###
##            GitHub: https://github.com/Digdgeo/Landsat8_Corrad_Embalses               ##
#                        Sevilla 01/01/2016-31/03/2016                                   #


#Con este script realizamos de un solo paso la descompresion y borrado de los tar.bz de las Landsat, el rename de la escenas y 
#La ejecucion del Protocolo para la Correccion Radiometrica. Va trabajando en bucle, de modo que hara todas las escenas
#Comprimidas en tar.bz que encuentre en el directorio (por defecto C:/Protocolo/ori). Por tanto la entrada sera una carpeta donde haya 
#Escenas comprimidas y la salida sera directamente el resultado de ejecutar la clase Landsat() usada para la Correccion Radiometrica. 
#Para ejecutarlo solo hay que abrir un cmd y escribir 'python rename_process.py'

import os, re, time, tarfile
from Protocolo import Landsat

def rename(path):

    '''Esta funcion hace el rename de escenas en una carpeta (por defecto 'C:\Embalses\ori'), desde su nomenclatura en formato USGS 
    al formato YearMonthDaySatPath_Row. Funciona para Landsat 5-8. Si hubiera algun problema como posibles escenas duplicadas, 
    imprime la escena que da error y pasa a la siguiente. Las escenas que va renombrando correctamente son impresas en tambien en pantalla

                    LC82020342014224LGN00 --->   20140812l8oli202_34

    '''
    print 'rename called'
    sats = {'LC8': 'l8oli', 'LE7': 'l7etm', 'LT5': 'l5tm'}
    fecha=time.strftime("%d-%m-%Y")
    raiz = os.path.split(path)[0]
    escena = os.path.split(path)[1]
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

    outname = os.path.join(raiz, year +  month  + day + sats[sat] + path + "_" + row)
    print outname

    try:

        os.mkdir(outname)
        return outname
        #os.rename(escena, outname)
        print 'Escena', escena, 'renombrada a', outname

    except Exception as e:
        print e, escena


def untar(ruta):

    '''Esta funcion realiza la descompresion y el borrado de los tar.bz originales. Descomprime los ficheros en una carpeta con el nombre
    en formato yearmonthdaysatpath_row que crea llamando a la funcion rename(), una vez descomprida la escena llama a la clase Landsat()
    y ejecuta el Protocolo para la correccion radiometrica'''
    
    print 'empezando la tarea'
    
    for i in os.listdir(ruta):

        if i.endswith('tar.gz') or i.endswith('.tar'):
            
            try:

                fname = os.path.join(ruta, i)
                tar = tarfile.open(fname)
                #nfname = os.path.join(os.path.split(fname)[0], os.path.split(fname)[1][:-7])
                nfname = rename(fname)
                #os.mkdir(nfname)
                os.chdir(nfname)
                tar.extractall()
                print i, 'descomprimido'
                tar.close()
                os.remove(fname)
                os.chdir(r'C:\Embalses')
                escena = Landsat(nfname)
                escena.run_all()
                
            except Exception as e:
                print e, escena
                continue

#path = os.getcwd() Se podria hacer en el directorio que se quisiera
if __name__ == "__main__":
    untar(r'C:\Protocolo\ori')