def get_kl_csw():
    
    #primero hacemos el recorte al dtm para que tenga la misma extension que la escena y poder operar con los arrays
    import subprocess, os, pandas, gdal, time, shutil
    import matplotlib.pyplot as plt
    import numpy as np

    t = time.time()
    shape = 'C:\\Protocolo\\data\\temp\\dtm_escena2.shp'
    ruta = 'C:\\Protocolo\\ori\\20140812l8oli202_34'

    for i in os.listdir(ruta):

        if i.endswith('B1.TIF'):
            raster = os.path.join(ruta, i)

    cmd = ["gdaltindex", shape, raster]
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=proc.communicate()
    exit_code=proc.wait()
    
    if exit_code: #Oops, something went wrong!
        raise RuntimeError(stderr)
    else:
        print stdout
        print 'marco generado'
    
    #ya tenemos el dtm recortado guardado en data/temp, ahora vamos a generar el hillshade. Para ello primero 
    #hay que recortar el dtm
    ruta = r'C:\Protocolo\data'
    dtm_escena = r'C:\Protocolo\data\temp\dtm_escena.img'
    for i in os.listdir(ruta):
        if i.endswith('full.img'):
            dtm = os.path.join(ruta, i)
            
    cmd = ["gdalwarp", "-dstnodata" , "0" , "-cutline", "-crop_to_cutline"]
    cmd.append(dtm)
    cmd.append(dtm_escena)
    cmd.insert(4, shape)
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=proc.communicate()
    exit_code=proc.wait()

    if exit_code: #Oops, something went wrong!
        raise RuntimeError(stderr)
    else:
        print stdout
        print 'dtm_escena generado'
    
    #Ya tenemos el dtm de la escena, ahora vamos a obtener el hillshade, primero debemos tomar los parámtros solares del MTL
    
    ruta = r'C:\Protocolo\ori\20140812l8oli202_34'

    for i in os.listdir(ruta):
        if i.endswith('MTL.txt'):
            mtl = os.path.join(ruta,i)
            arc = open(mtl,'r')
            for i in arc:
                if 'SUN_AZIMUTH' in i:
                    azimuth = float(i.split("=")[1])
                elif 'SUN_ELEVATION' in i:
                    elevation = float(i.split("=")[1])
    print azimuth, elevation       
    #Una vez tenemos estos parámetros generamos el hillshade
    ruta = r'C:\Protocolo\data\temp'
    salida = r'C:\Protocolo\data\temp\hillshade.img'
    #for i in os.listdir(ruta):
        #if i.endswith('2.img'):
            #dtm = os.path.join(ruta, i)
    cmd = ["gdaldem", "hillshade", "-az", "-alt", "-of", "ENVI"]
    cmd.append(dtm_escena)
    cmd.append(salida)
    cmd.insert(3, str(azimuth))
    cmd.insert(5, str(elevation))
    #print cmd
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=proc.communicate()
    exit_code=proc.wait()
    
    if exit_code: 
        raise RuntimeError(stderr)
    else:
        print stdout
        print 'hillshade generado'
    
    #Ya está el hillshade en data/temp. También tenemos ya la Fmask generada en ori, así que ya podemos operar con los arrays
    ruta = r'C:\Protocolo\ori\20140812l8oli202_34'
    for i in os.listdir(ruta):
        if i.endswith('MTLFmask'):
            rs = os.path.join(ruta, i)
            print rs
            fmask = gdal.Open(rs)
            Fmask = fmask.ReadAsArray()
    ruta = r'C:\Protocolo\data\temp'
    for i in os.listdir(ruta):
        if i.endswith('shade.img'):
            rst = os.path.join(ruta, i)
            print rst
            hillshade = gdal.Open(rst)
            Hillshade = hillshade.ReadAsArray()
    
    #Queremos los pixeles de cada banda que esten dentro del valor agua (1) y sin nada definido ((0) 
    #para las sombras) de la Fmask (con lo cual también excluimos las nubes y sombras de nubes). 
    #Junto con estos valores, queremos también los valores que caen en sombra (se ha decidido que 
    #el valor de corte más adecuado es el percentil 20)
    
    #Arriba estamos diciendo que queremos el mínimo del agua o de la escena completa sin nubes ni 
    #sombras ni agua pero en sombra orográfica
    
    #Ahora vamos a aplicar la máscara y hacer los histogramas
    ruta = r'C:\Protocolo\ori\20140812l8oli202_34'
    bandas = ['B1', 'B2', 'B3', 'B4','B5', 'B6', 'B6', 'B7', 'B9']
    lista_kl = []
    for i in os.listdir(ruta):
        banda = i[-6:-4]
        if banda in bandas:
            raster = os.path.join(ruta, i)
            bandraster = gdal.Open(raster)
            data = bandraster.ReadAsArray()
            data2 = data[(((Fmask==1) | ((Fmask==0)) & (Hillshade<(np.percentile(Hillshade, 20)))))]
            lista_kl.append(data2.min())#añadimos el valor minimo (podría ser perceniles) a la lista de kl
            lista = sorted(data2.tolist())
            #nmask = (data2<lista[1000])#pobar a coger los x valores más bajos, a ver hasta cual aguanta bien
            data3 = data2[data2<lista[1000]]
            #Histogramas
            df = pandas.DataFrame(data3)
            #plt.figure(); df.hist(figsize=(10,8), bins = 100)#incluir titulo y rotulos de ejes
            plt.figure(); df.hist(figsize=(10,8), bins = 50, cumulative=False, color="Red"); 
            plt.title('20140812l8oli202_34_gr_' + banda, fontsize = 18)
            plt.xlabel("Pixel Value", fontsize=16)  
            plt.ylabel("Count", fontsize=16)

            name = r'C:\Protocolo\rad2\20140812l8oli202_34_gr_' + banda.lower() + '.png'
            plt.savefig(name)
    plt.close('all')
    print 'Histogramas generados'
        
    #Hasta aqui tenemos los histogramas generados y los valores minimos guardados en lista_kl, ahora 
    #debemos escribir los valores minimos de cada banda en el archivo kl.rad
    ruta = r'C:\Protocolo\rad'
    for i in os.listdir(ruta):
            
            if i.endswith('.rad'):

                archivo = os.path.join(ruta, i)
                dictio = {6: lista_kl[0], 7: lista_kl[1], 8: lista_kl[2], 9: lista_kl[3], \
                          10: lista_kl[4], 11: lista_kl[5], 12: lista_kl[6], 14: lista_kl[7]}

                rad = open(archivo, 'r')
                rad.seek(0)
                lineas = rad.readlines()

                for l in range(len(lineas)):

                    if l in dictio.keys():
                        lineas[l] = lineas[l].rstrip()[:-4] + str(dictio[l]) + '\n'
                    else: continue

                rad.close()

                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                
                src = os.path.join(ruta, i)
                path_rad = os.path.join(ruta, '20140812l8oli202_34')
                if not os.path.exists(path_rad):
                    os.makedirs(path_rad)
                dst = os.path.join(path_rad, '20140812l8oli202_34_kl.rad')
                shutil.copy(src, dst)
                    
    print 'modificados los metadatos del rad'
    
    ruta = r'C:\Protocolo\data\temp'
    for i in os.listdir(ruta):
        arz = os.path.join(ruta, i)
        os.remove(arz)
    
    print 'Finalizado en ' + str(time.time()-t) + ' segundos'