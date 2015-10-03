import os, time, re

def rename(ruta):

    '''Este metodo hace el rename de las escenas en ori, desde su nomenclatura en formato USGS al formato usado
    en el LAST'''

    sats = {'LC8': 'l8oli', 'LE7': 'l7etm', 'LT5': 'l5tm'}
    fecha=time.strftime("%d-%m-%Y")
    
    
    for i in os.listdir(ruta):
    
        if re.search("^L\S[0-9]", i) and os.path.isdir(os.path.join(ruta, i)):
            
            escena = os.path.join(ruta, i)
            sat = i[:3]
            path =  i[3:6]
            row = i[7:9]
            fecha = time.strptime(i[9:13] + " " + i[13:16], '%Y %j')
            year = str(fecha.tm_year)
            month = str(fecha.tm_mon)
            if len(month) == 1:
                month = '0' + month
            day = str(fecha.tm_mday)
            if len(day) == 1:
                day = '0' + day

            outname = os.path.join(ruta, year +  month  + day + sats[sat] + path + "_" + row)
            os.rename(escena, outname)