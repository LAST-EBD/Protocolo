import os, glob, string

ruta = raw_input("Carpeta con ficheros a renombrar: ")
#fecha = raw_input("introduzca el la fecha de la imagen (yyyy/mm/dd): ")

indice = string.find(ruta, "\\", -21)
escena = ruta[indice+1:]

sat = escena[8:10].upper()
path =  escena[-6:-3]
row = "0" + escena[-2:]
year = escena[:4]
month = escena[4:6]
day = escena[6:8]
sensor = escena[10:-6].lower()



os.chdir(ruta)
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