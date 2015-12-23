############## PROTOCOLO AUTOMATICO PARA LA NORMALIZACION DE ESCENAS LANDSAT 7 Y 8 ##############
#######                                                                                   #######
###### Proyecto Lifewatch Observatorio del Cambio Global                                   ###### 
##### laboratorio de SIG y Teledeteccion de la Estacion Biologica de Doñana                 #####
#### Autor: Diego Garcia Diaz                                                                ####
### email: diegogarcia@ebd.csic.es                                                            ###
## GitHub: https://github.com/LAST-EBD/Protocolo                                               ##
# Sevilla 01/10/2014-30/11/2015

def gapfill():

    ''' Esta funcion realiza todo el proceso necesario para ejecutar el Gapfill (Maxwell 2004), desde el rename previo
    a la propia llamada al gapfill, y los renames posteriores junto con la creacion de carpetas y movimiento de archivos, de modo 
    que cuando acabe de ejecutarse, ya estara la escena lista para aplicarle el Protocolo Automatico''' 

    import os, glob, string, subprocess

    #Aqui le metemos el rename ya hecho, luego ejecutamos
    os.system('./L7gapfil')
    base = '/home/last/Escritorio/landsat7'
    for i in os.listdir(base):
        escena = i
        ruta_escena = os.path.join(base, escena)
	print 'ruta_escena: ', ruta_escena

    sat = escena[8:10].upper()
    path =  escena[-6:-3]
    row = "0" + escena[-2:]
    year = escena[:4]
    month = escena[4:6]
    day = escena[6:8]
    sensor = escena[10:-6].lower()

    print sat, path, row, year, month, day, sensor

    os.chdir(ruta_escena)
    archivosimg=glob.glob('*.TIF')
    archivostxt=glob.glob('*.txt')

    for fileimg in archivosimg:

        if "_B7" in fileimg or "_B8" in fileimg:
	    os.rename(fileimg, sat + "2" + path + row + "_" + row + year + month + day + "_" + fileimg[-6:-4] + "0" + ".TIF")
	elif "_VCID_2" in fileimg:
	    os.rename(fileimg, sat + "2" + path + row + "_" + row + year + month + day + "_" + fileimg[-13:-11] + "2" + ".TIF")
	elif "_VCID_1" in fileimg:
	    os.rename(fileimg, sat + "1" + path + row + "_" + row + year + month + day + "_" + fileimg[-13:-11] + "1" + ".TIF")
	else:
	    os.rename(fileimg, sat + "1" + path + row + "_" + row + year + month + day + "_" + fileimg[-6:-4] + "0" + ".TIF")

    for filetxt in archivostxt:

        if "_GCP" in filetxt:
            os.rename(filetxt, sat + "1" + path + row + "_" + row + year + month + day + "_" + "GCP" + ".txt")
	elif "_MTL" in filetxt:
	    os.rename(filetxt, sat + "1" + path + row + "_" + row + year + month + day + "_" + "MTL" + ".txt")

    print 'Archivos renombrados para ejecutar el gapfill\n'
    print '---------------------------------------------------------\n'


    #escena = '20150101l7etm202_34'#sacamos la escena y la b1 de "escena"
    #b1 = 'L71202034_03420150101_B10.TIF'

    #sacamos la banda1
    for i in os.listdir(ruta_escena):

        if 'B10' in i:

            b1 = i
	    print 'b1: ', b1

    #buscamos el archivo input.odl para modificarlo
    ruta_odl = '/gapfil'

    for i in os.listdir(ruta_odl):

	print i

        if i.endswith('put.odl'):

            arc = os.path.join(ruta_odl, i)
	    print 'ODL:', arc, 'ESCENA', str(escena), 'B1: ', b1
	    odl = open(arc, 'r')
	    lineas = odl.readlines()
	    for i in lineas:
		    print i
	    for n, e in enumerate(lineas):

	        if 'WO_DIRECTORY' in lineas[n]:
		    lineas[n] = '    WO_DIRECTORY = "/home/last/Escritorio/landsat7/' + str(escena) + '"\n'
	        elif 'GAPFILL_IMAGE' in lineas[n]:
		    lineas[n] = '    GAPFILL_IMAGE = "' + str(b1) + '"\n'
	    else:
		continue

    arc = '/gapfil/input.odl'
    f = open(arc, 'w')
    for linea in lineas:
        print linea.rstrip()
        f.write(linea)
    f.close()

    print 'input.odl modificado\n'
    print '---------------------------------------------------------\n'

    #ASEGURARSE DE ABRIR EL CMD COMO SUDO SU (SUPER USER)
    #una vez cambiado el gapfill llamamos al ./L7gapfill
    os.chdir(ruta_odl)

    os.system('./L7gapfill input.odl')
    print 'Gapfill finalizado\n'
    print '---------------------------------------------------------\n'

    #Creamos la estructura de las carpetas y movemos los archivos a ellas
    os.chdir(ruta_escena)
    os.mkdir('gapfill')
    ruta_gapfill = os.path.join(ruta_escena, 'gapfill')

    for i in os.listdir(ruta_escena):

        if 'SEG' in i:

            src = os.path.join(ruta_escena, i)
            dst = os.path.join(ruta_gapfill, i)

            os.rename(src, dst)

    #borramos las seg_mask
    for i in os.listdir(ruta_gapfill):

        if i.startswith('gapmask'):

            arc = os.path.join(ruta_gapfill, i)
            os.remove(arc)

    #Hacemos el rename
    for i in os.listdir(ruta_escena):
        if i.endswith('MTL.txt'):
            mtl = os.path.join(ruta_escena, i)
            arc = open(mtl,'r')
            for i in arc:
                if 'LANDSAT_SCENE_ID' in i:
                    usgs_id = i[-23:-2]

    dgapfill = {'B10': '_B1.TIF', 'B20': '_B2.TIF', 'B30': '_B3.TIF', 'B40': '_B4.TIF', 'B50': '_B5.TIF',\
             'B61': '_B6_VCID_1.TIF', 'B62': '_B6_VCID_2.TIF', 'B70': '_B7.TIF', 'B80': '_B8.TIF'}

    #Rename en escena
    for i in os.listdir(ruta_escena):

        if i.endswith('.TIF'):

            banda = i[-7:-4]
            raster = os.path.join(ruta_escena, i)
            print raster
            salida = os.path.join(ruta_escena, usgs_id + dgapfill[banda])
            print salida
            os.rename(raster, salida)

    #Rename en gapfill
    for i in os.listdir(ruta_gapfill):

        if i.endswith('.TIF'):

            banda = i[-7:-4]
            raster = os.path.join(ruta_gapfill, i)
            print raster
            salida = os.path.join(ruta_gapfill, usgs_id + dgapfill[banda])
            print salida
            os.rename(raster, salida)

    #Extraemos los archivos comprimidos

    path = os.path.join(ruta_escena, 'gap_mask')
    os.chdir(path)

    for i in os.listdir(path):

        cmd = []
        cmd.append('gzip')#funciona tanto con este como con winrar, probar a cambiar el path de salida o cambiar el cwd
        cmd.append('-d')
        cmd.append(os.path.join(path, i))

        print cmd

        subprocess.check_call(cmd)

    #borramos los rar y la banda 8 en TIF
    for i in os.listdir(path):
        if i.endswith('B8.TIF'):
            arc = os.path.join(path, i)
            os.remove(arc)

    print 'Estructura de archivos necesaria para correr el Protocolo automatico creada\n'
    print '---------------------------------------------------------\n'''

#llamamos a la funcion gapfill'''
if __name__ == '__main__':
    gapfill()
