######### PROTOCOLO AUTOMATICO PARA LA NORMALIZACION DE ESCENAS LANDSAT 7 Y 8 ########
#######                                                                        #######
###### Proyecto Lifewatch Observatorio del Cambio Global                        ###### 
##### laboratorio de SIG y Teledeteccion de la Estacion Biologica de Donana      #####
#### Autor: Diego Garcia Diaz                                                     ####
### email: diegogarcia@ebd.csic.es                                                 ###
## GitHub: https://github.com/LAST-EBD/Protocolo                                    ##
# Sevilla 01/10/2014-30/11/2015                                                      #

#coding utf-8

import os, shutil, re, time, subprocess, pandas, rasterio, pymongo, sys, fileinput, stat, urllib2
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy import ndimage
from osgeo import gdal, gdalconst, ogr
from pymasker import landsatmasker, confidence
from datetime import datetime
from IPython.display import Image
from IPython.display import display


class Landsat(object):
    
     
    '''Esta clase esta hecha para ser usada como alternativa automatizada al protocolo para tratamiento de imagenes landsat del
    Laboratorio de SIG y Teledeteccion de la Estacion Biologica de Donana. La normalizacion consta de 4 metodos: Importacion, Reproyeccion
    Correccion Radiometrica y Normalizacion. 

    El unico software necesario es Miramon, que se utiliza por su gestion de Metadatos. Se emplea en la Importacion y en la Correccion Radiometrica
    y se llama mediante archivos bat. Para el resto de procesos se usan GDAL, Rasterio y otras librerias de Python. En general se tratan los rasters
    como arrays, lo que produce un rendimiento en cuanto a la velocidad de procesado bastante elevado. Para la normalizacion se emple tambien una 
    mascara de nubes, que se obtiene empleando Fmask o la banda de calidad de Landsat 8 si fallara Fmask.

    El script requiere una estructura de carpetas en un mismo nivel (/ori, /geo, /rad, /nor y /data). En /data deben de estar los archivos necesarios para
    llevar a cabo la normalizacion:

        1) Escena de referencia Landsat 7 /20020718l7etm202_34, en formato img + doc + rel + hdr 
        2) Shape con los limites del Parque Nacional de Donana para calcular la cobertura de nubes sobre Donana
        3) Modelo Digital del Terreno lo bastante amplio como para englobar cualquier escena
        4) Mascaras equilibradas y no equilibradas y de tipos de areas pseudo invariantes

    Ademas de estos requisitos, en la carpeta /rad debe de haber 2 archivos kl_l8.rad y kl_l7.rad donde se guardaran temporalmente los valores
    del objeto oscuro (proceso empleado para la Correccion Radiometrica) y el dtm de la escena. Si la escena es una Landsat 7 debe de tener una carpeta
    /gapfill donde se encuentren las bandas originales con el bandeado del gapfill corregido y la carpeta gapmask con las mascaras de esos gaps, ya 
    que se emplearan para una correcta busqueda del objeto oscuro.

    Al finalizar el proceso tendremos en ori, geo, rad y nor las bandas en formato img + doc + rel + hdr pasadas ya de niveles digitales
    a reflectancia en superficie normalizada y toda la informacion del proceso almacenada en una base de datos MongoDB'''
    
    def __init__(self, ruta, umbral=50, hist=1000):
        
        
		'''Instanciamos la clase con la escena que vayamos a procesar, hay que introducir la ruta a la escena en ori
		y de esa ruta el constructor obtiene el resto de rutas que necesita para ejecutarse. Los parametros marcados por defecto son el 
		umbral para la mascara de nubes Fmask y el numero de elementos a incluir en el histograma de las bandas'''
		self.ruta_escena = ruta
		self.ori = os.path.split(ruta)[0]
		self.escena = os.path.split(ruta)[1]
		self.raiz = os.path.split(self.ori)[0]
		self.geo = os.path.join(self.raiz, 'geo')
		self.rad = os.path.join(self.raiz, 'rad')
		self.nor = os.path.join(self.raiz, 'nor')
		self.data = os.path.join(self.raiz, 'data')
		self.umbral = umbral
		self.hist = hist
		#metemos una variable que almacene el tipo de satelite
		if 'l7etm' in self.escena:
			self.sat = 'L7'
			if self.escena > '20030714':
				self.gapfill = os.path.join(self.ruta_escena, 'gapfill')
			else:
				self.gapfill = self.ruta_escena
		elif 'l8oli' in self.escena:
			self.sat = 'L8'
		elif 'l5tm' in self.escena:
			self.sat = 'L5'
		else:
			print ' No reconozco el satelite'
		 
		if self.sat == 'L7' and self.escena > '20030714':
			self.mimport = os.path.join(self.gapfill, 'miramon_import')
		else:
			self.mimport = os.path.join(self.ruta_escena, 'miramon_import')
		if not os.path.exists(self.mimport):
			os.makedirs(self.mimport)

		print self.sat, self.escena
		self.bat = os.path.join(self.ruta_escena, 'import.bat')
		self.bat2 = os.path.join(self.rad, 'importRad.bat')
		self.equilibrado = os.path.join(self.data, 'equilibrada.img')
		self.noequilibrado = os.path.join(self.data, 'MASK_1.img')
		self.parametrosnor = {}
		self.iter = 1
		self.cloud_mask = 'Fmask' 
		for i in os.listdir(self.ruta_escena):
			#print i
			if i.endswith('MTL.txt'):
				mtl = os.path.join(self.ruta_escena,i)
				#print mtl
				arc = open(mtl,'r')
				for i in arc:
					if 'LANDSAT_SCENE_ID' in i:
						usgs_old_id = i[-23:-2] #este es el antiguo nombre de Landsat
					elif 'LANDSAT_PRODUCT_ID' in i:
						usgs_new_id = i.split('=')[-1][2:-2]
					elif 'CLOUD_COVER' in i:
						cloud_scene = float(i[-6:-1])
					elif 'PROCESSING_SOFTWARE_VERSION' in i:
						lpgs = i.split('=')[1][2:-2]
		arc.close()
		#Vamos a bajar el quicklook de la escena disponible en usgs.explorer y a guardarlo en la carpeta ori
		print 'Ahora vamos a guardar la captura'
		self.quicklook = os.path.join(self.ruta_escena, usgs_old_id + '.jpg')

		######### DESCOMENTAR ESTAS LINEAS PARA GUARDAR EL QUICKLOOK!!!!!!!!!!!!!!!!#####################
		if self.sat == 'L7':
			sensor = 'etm'
		elif self.sat == 'L5' or self.sat == 'L4':
			sensor = 'tm'
		
		qcklk = open(self.quicklook,'wb')
		if self.sat == 'L8':
			s = 'https://earthexplorer.usgs.gov/browse/landsat_8/{}/202/034/{}.jpg'.format(self.escena[:4], usgs_new_id)
			print s
		else:
			s = 'https://earthexplorer.usgs.gov/browse/{}/202/34/{}/{}_REFL.jpg'.format(sensor, self.escena[:4], usgs_new_id)
			print s
		#intento corregir dab(2017/01/10)el error qcklk.write(urllib.request.urlopen(s).read())
		u2=urllib2.urlopen(s)
		junk=u2.read()
		qcklk.write(junk)
		qcklk.close()
		display(Image(url=s, width=500))

		#copiamos el mtl a la carpeta gapfill
		if self.sat == 'L7' and self.escena > '20030714':
			
			dst = os.path.join(self.gapfill, os.path.split(mtl)[1])
			shutil.copy(mtl, dst)

		self.newesc = {'_id': self.escena, 'usgs_id': usgs_old_id, 'lpgs': lpgs, 'Clouds': {'cloud_scene': cloud_scene},\
					   'Info': {'Tecnico': 'LAST-EBD Auto', 'Iniciada': datetime.now(),'Pasos': {'geo': '', 'rad': '', 'nor': ''}}}

		#iniciamos MongoDB desde el propio script... 
		#os.system('mongod')
		# Conectamos con MongoDB 
		connection = pymongo.MongoClient("mongodb://localhost")

		# DataBase: teledeteccion, Collection: landsat

		db=connection.teledeteccion
		landsat = db.landsat

		try:

			landsat.insert_one(self.newesc)

		except Exception as e:
			
			landsat.update_one({'_id':self.escena}, {'$set':{'Info.Iniciada': datetime.now()}})
			#print "Unexpected error:", type(e), se Podria dar un error por clave unica, por eso en
			#ese caso, lo que hacemos es actualizar la fecha en la que tratamos la imagen
            
            
    def fmask(self):
        
        '''-----\n
        Este metodo genera el algortimo Fmask que sera el que vendra por defecto en la capa de calidad de
        las landsat a partir del otono de 2015'''
        
        if self.sat == 'L7' and self.escena > '200030714':
            os.chdir(self.gapfill)
        else:
            os.chdir(self.ruta_escena)
            
        print 'comenzando Fmask'
        try:
            
            print 'comenzando Fmask'
            t = time.time()
                #El valor (el ultimo valor, que es el % de confianza sobre el pixel (nubes)) se pedira desde la interfaz que se haga. 
            a = os.system('C:/Cloud_Mask/Fmask 1 1 0 {}'.format(self.umbral))
            a
            if a == 0:
                
                print 'Mascara de nubes (Fmask) generada en ' + str(t-time.time()) + ' segundos'
     
            else:
                
                print 'comenzando BQA'
                for i in os.listdir(self.ruta_escena):
                    if i.endswith('BQA.TIF'):
                        masker = landsatmasker(os.path.join(self.ruta_escena, i))
                        mask = masker.getcloudmask(confidence.high, cirrus = True, cumulative = True)
                        masker.savetif(mask, os.path.join(self.ruta_escena, self.escena + '_Fmask.TIF'))
                self.cloud_mask = 'BQA'
                print 'Mascara de nubes (BQA) generada en ' + str(t-time.time()) + ' segundos'
                                       
        except Exception as e:
            
            print "Unexpected error:", type(e), e
            
            
    
        #Insertamos el umbral para Fmask en la base de datos: Si es de calidad pondremos 'BQA'
        connection = pymongo.MongoClient("mongodb://localhost")
        db=connection.teledeteccion
        landsat = db.landsat
        
        try:
            if a != 0:
                self.umbral = 'BQA'
            
            landsat.update_one({'_id':self.escena}, {'$set':{'Clouds.umbral': self.umbral}},  upsert=True)
            
        except Exception as e:
            
            print "Unexpected error:", type(e), e
    
    
    def fmask_legend(self, path):
        
        '''-----\n
        Este metodo anade las lineas necesarias para que Envi reconozca que es una raster categorico con sus
        correspondientes valores (Sin definir, Agua, Sombra de nubes, Nieve, Nubes). Se aplicara tanto a la fmask 
        generada en ori, como a la reproyectada en nor'''
        
        for i in os.listdir(path):
    
            if i.endswith('Fmask.hdr'):

                fmask = os.path.join(path, i)
                doc = open(fmask, 'r')
                doc.seek(0)
                lineas = doc.readlines()
                
                for n,e in enumerate(lineas):#Establecemos el tipo como clasificacion, realmente, en Envi 5 al menos, no importa
                    if e.startswith('file type'):
                        lineas[n] = 'file type: ENVI Classification\n'

                nodata = '\ndata ignore value = 255\n'
                clases = 'classes = 5\n'
                lookup = 'class lookup = {255,255,255, 0,0,255, 0,0,0, 0,255,255, 150,150,150}\n'
                vals = 'class names = {Unclassified, Water, Shadow, Snow, Cloud}\n'

                lineas.append(nodata)
                lineas.append(clases)
                lineas.append(lookup)
                lineas.append(vals)

                doc.close()

                f = open(fmask, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                
            elif i.endswith('Fmask'):#Anadimos el .img  la Fmask porque David lo quiere...
                
                src = os.path.join(path, i)
                dst = src + '.img'
                os.rename(src, dst)
                
                
    def get_cloud_pn(self):
        
        '''-----\n
        Este metodo recorta la fmask con el shp del Parque Nacional, para obtener la cobertura nubosa en Parque Nacional en el siguiente paso'''
        
        shape = os.path.join(self.data, 'Limites_PN_Donana.shp')
        crop = "-crop_to_cutline"
        
        if self.sat == 'L7' and self.escena > '20030714':
            ruta = self.gapfill
        else:
            ruta = self.ruta_escena
            
        for i in os.listdir(ruta):
            if i.endswith('Fmask.img') | i.endswith('Fmask.TIF'):
                cloud = os.path.join(ruta, i)
        #usamos Gdalwarp para realizar las mascaras, llamandolo desde el modulo subprocess
        cmd = ["gdalwarp", "-dstnodata" , "0" , "-cutline", ]
        path_masks = os.path.join(ruta, 'masks')
        if not os.path.exists(path_masks):
            os.makedirs(path_masks)

        
        salida = os.path.join(path_masks, 'cloud_PN.TIF')
        cmd.insert(4, shape)
        cmd.insert(5, crop)
        cmd.insert(6, cloud)
        cmd.insert(7, salida)

        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=proc.communicate()
        exit_code=proc.wait()

        if exit_code: 
            raise RuntimeError(stderr)
                          
        
        ds = gdal.Open(salida)
        cloud = np.array(ds.GetRasterBand(1).ReadAsArray())
        
        if self.cloud_mask == 'BQA':
            mask = (cloud == 1)
        elif self.cloud_mask == 'Fmask': 
            mask = (cloud == 2) | (cloud == 4)
        else:
            print 'No hay mascara de nubes... Pero esto que es!?'
        
        cloud_msk = cloud[mask]
        print cloud_msk.size
        clouds = float(cloud_msk.size*900)
        PN = 534158729.313 
        pn_cover = round((clouds/PN)*100, 2)
        ds = None
        cloud = None
        cloud_msk = None
        clouds = None
        #Insertamos la cobertura de nubes en la BD
        connection = pymongo.MongoClient("mongodb://localhost")
        db=connection.teledeteccion
        landsat = db.landsat
        
        try:
        
            landsat.update_one({'_id':self.escena}, {'$set':{'Clouds.cloud_PN': pn_cover}},  upsert=True)
            
        except Exception as e:
            print "Unexpected error:", type(e), e
            
        print "El porcentaje de nubes en el Parque Nacional es de " + str(pn_cover)
        
        
    def createI_bat(self):
        
        '''-----\n
        Este metodo crea un archivo bat con los parametros necesarios para realizar la importacion'''
        
        if self.sat == 'L7' and self.escena > '20030714':
            ruta = self.gapfill
        else:
            ruta = self.ruta_escena
            
        #estas son las variables que necesarias para crear el bat de Miramon
        tifimg = 'C:\\MiraMon\\TIFIMG'
        num1 = '9'
        num2 = '1'
        num3 = '0'
        salidapath = self.mimport #aqui va la ruta de salida de la escena
        dt = '/DT=c:\\MiraMon'

        for i in os.listdir(ruta):
            if i.endswith('B1.TIF'):
                banda1 = os.path.join(ruta, i)
            elif i.endswith('MTL.txt'):
                mtl = "/MD="+ruta+"\\"+i
            else: continue

        lista = [tifimg, num1, banda1,  salidapath, num2, num3, mtl, dt]
        print lista

        batline = (" ").join(lista)

        pr = open(self.bat, 'w')
        pr.write(batline)
        pr.close()


    def callI_bat(self):
        
        '''-----\n
        Este metodo llama ejecuta el bat de la importacion. Tarda entre 7 y 21 segundos en importar la escena'''

        #import os, time
        ti = time.time()
        a = os.system(self.bat)
        a
        if a == 0:
            print "Escena importada con exito en " + str(time.time()-ti) + " segundos"
        else:
            print "No se pudo importar la escena"
        #borramos el archivo bat creado para la importacion de la escena, una vez se ha importado esta
        os.remove(self.bat)
        
    def get_kl_csw(self):
        
        '''Este metodo obtiene los Kl para cada banda. Lo hace buscando los valores minimos dentro 
        de las zonas clasificadas como agua y sombra orografica, siempre y cuando la sombra orografica 
        no este cubierta por nubes ni sombra de nubes. La calidad de la mascara e muy importante, por eso
        a las escenas que no se puedan realizar con Fmask habria que revisarles el valor de kl.
        Tambien distingue Landsar 7 de Landsat 8, aplicandole tambien a las Landsat 7 la mascara de Gaps'''
    
    #Empezamos borrando los archivos de temp, la idea de esto es que al acabar una escena queden disponibles
    #por si se quiere comprobar algo. Ya aqui se borran antes de comenzar la siguiente
        t = time.time()

        temp = os.path.join(self.data, 'temp')
        for i in os.listdir(temp):
            arz = os.path.join(temp, i)
            os.remove(arz)

        #Hacemos el recorte al dtm para que tenga la misma extension que la escena y poder operar con los arrays
        t = time.time()
        shape = os.path.join(temp, 'poly_escena.shp')
        
        if self.sat == 'L7' and self.escena > '20030714':
            ruta = self.gapfill
        else:
            ruta = self.ruta_escena

        for i in os.listdir(ruta):

            if i.endswith('B1.TIF'):
                raster = os.path.join(ruta, i)

        cmd = ["gdaltindex", shape, raster]
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=proc.communicate()
        exit_code=proc.wait()

        if exit_code: 
            raise RuntimeError(stderr)
        else:
            print stdout
            print 'marco generado'

        #ya tenemos el dtm recortado guardado en data/temp, ahora vamos a generar el hillshade.  
        #Para ello primero hay que recortar el dtm con el shape recien obtenido con la extension de la escena
        dtm_escena = os.path.join(temp, 'dtm_escena.img')
        for i in os.listdir(self.data):
            if i.endswith('full.img'):
                dtm = os.path.join(self.data, i)

        cmd = ["gdalwarp", "-dstnodata" , "0" , "-cutline", "-crop_to_cutline"]
        cmd.append(dtm)
        cmd.append(dtm_escena)
        cmd.insert(4, shape)
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=proc.communicate()
        exit_code=proc.wait()

        if exit_code: 
            raise RuntimeError(stderr)
        else:
            print stdout
            print 'dtm_escena generado'

        #Ahora ya tenemos el dtm de la escena, a continuacion vamos a obtener el hillshade 
        #primero debemos tomar los parametros solares del MTL
        for i in os.listdir(ruta):
            if i.endswith('MTL.txt'):
                mtl = os.path.join(ruta,i)
                arc = open(mtl,'r')
                for i in arc:
                    if 'SUN_AZIMUTH' in i:
                        azimuth = float(i.split("=")[1])
                    elif 'SUN_ELEVATION' in i:
                        elevation = float(i.split("=")[1])

        #Una vez tenemos estos parametros generamos el hillshade
        salida = os.path.join(temp, 'hillshade.img')
        cmd = ["gdaldem", "hillshade", "-az", "-alt", "-of", "ENVI"]
        cmd.append(dtm_escena)
        cmd.append(salida)
        cmd.insert(3, str(azimuth))
        cmd.insert(5, str(elevation))
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=proc.communicate()
        exit_code=proc.wait()

        if exit_code: 
            raise RuntimeError(stderr)
        else:
            print stdout
            print 'Hillshade generado'

        #Ya esta el hillshade en data/temp. Tambien tenemos ya la Fmask generada en ori, 
        #asi que ya podemos operar con los arrays
        for i in os.listdir(ruta):
            if i.endswith('MTLFmask.img') | i.endswith('_Fmask.TIF'):
                rs = os.path.join(ruta, i)
                fmask = gdal.Open(rs)
                Fmask = fmask.ReadAsArray()
                print 'min, max: ', Fmask.min(), Fmask.max()
        for i in os.listdir(temp):
            if i.endswith('shade.img'):
                rst = os.path.join(temp, i)
                print rst
                hillshade = gdal.Open(rst)
                Hillshade = hillshade.ReadAsArray()

        #Queremos los pixeles de cada banda que esten dentro del valor agua (1) y sin nada definido ((0) 
        #para las sombras) de la Fmask (con lo cual tambien excluimos las nubes y sombras de nubes). 
        #Junto con estos valores, queremos tambien los valores que caen en sombra (se ha decidido que 
        #el valor de corte mas adecuado es el percentil 20)

        #Arriba estamos diciendo que queremos el minimo del agua o de la escena completa sin nubes ni 
        #sombras ni agua pero en sombra orografica

        #Ahora vamos a aplicar la mascara y hacer los histogramas
        if self.sat == 'L8':
            bandas = ['B1', 'B2', 'B3', 'B4','B5', 'B6', 'B6', 'B7', 'B9']
            lista_kl = []
            for i in os.listdir(ruta):
                banda = i[-6:-4]
                if banda in bandas:
                    raster = os.path.join(ruta, i)
                    bandraster = gdal.Open(raster)
                    data = bandraster.ReadAsArray()
                    #anadimos la distincion entre Fmask y BQA
                    if self.cloud_mask == 'Fmask':
                        print 'usando Fmask'
                        data2 = data[((Fmask==1) | (((Fmask==0)) & (Hillshade<(np.percentile(Hillshade, 20)))))]

                    else:
                        print 'usando BQA\ngenerando water mask'

                        for i in os.listdir(ruta):
                            if i.endswith('BQA.TIF'):
                                masker = landsatmasker(os.path.join(ruta, i))  
                                maskwater = masker.getwatermask(confidence.medium) #cogemos la confianza media, a veces no hay nada en la alta
                                #print 'watermin, watermax: ', maskwater.min(), maskwater.max()

                                data2 = data[((data != 0) & ((maskwater==1) | (((Fmask==0)) & (Hillshade<(np.percentile(Hillshade, 20))))))]
                                print 'data2: ', data2.min(), data2.max(), data2.size

                    print 'data 2 obtenido'
                    lista_kl.append(data2.min())#anadimos el valor minimo (podria ser perceniles) a la lista de kl
                    lista = sorted(data2.tolist())
                    print 'lista: ', lista[:10]
                    #nmask = (data2<lista[1000])#probar a coger los x valores mas bajos, a ver hasta cual aguanta bien
                    data3 = data2[:self.hist]
                    print 'data3: ', data3.min(), data3.max()

                    df = pandas.DataFrame(lista[:10000])
                    #plt.figure(); df.hist(figsize=(10,8), bins = 100)#incluir titulo y rotulos de ejes
                    plt.figure(); df.hist(figsize=(10,8), bins = 20, cumulative=False, color="Red"); 
                    plt.title(self.escena + '_gr_' + banda, fontsize = 18)
                    plt.xlabel("Pixel Value", fontsize=16)  
                    plt.ylabel("Count", fontsize=16)
                    path_rad = os.path.join(self.rad, self.escena)
                    if not os.path.exists(path_rad):
                        os.makedirs(path_rad)
                    name = os.path.join(path_rad, self.escena + '_gr_'+ banda.lower() + '.png')
                    plt.savefig(name)

            plt.close('all')
            print 'Histogramas generados'

        #Hasta aqui tenemos los histogramas generados y los valores minimos guardados en lista_kl, ahora 
        #debemos escribir los valores minimos de cada banda en el archivo kl.rad
            for i in os.listdir(self.rad):

                    if i.endswith('l8.rad'):

                        archivo = os.path.join(self.rad, i)
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

                        src = os.path.join(self.rad, i)
                        dst = os.path.join(path_rad, self.escena + '_kl.rad')
                        shutil.copy(src, dst)

            print 'modificados los metadatos del archivo kl.rad\nProceso finalizado en ' + str(time.time()-t) + ' segundos'
            
        elif self.sat == 'L7' and self.escena > '20030714': 

            #self.hist = 1000000
            ####elegimos la mascara de gapnodata
            lista = []
            bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6_VCID_1', 'B6_VCID_2', 'B7']
            ruta_gap = os.path.join(self.ruta_escena, 'gap_mask')
            gap_bandas = [i for i in os.listdir(ruta_gap)]
            mydict = dict(zip(bands, gap_bandas))
            for n, e in enumerate(mydict):
                with rasterio.open(os.path.join(ruta_gap, mydict[e])) as src:
                        bands[n] = src.read()
                        lista.append(bands[n])

            gaps = sum(lista)
            print 'GAPS: ', gaps.min(), gaps.max()
            gaps[gaps!=8] = 0
            gaps[gaps==8] = 1
            print 'GAPS_reclassify: ', gaps.min(), gaps.max()
            #Hacemos el erode
            erode = ndimage.grey_erosion(gaps, size=(5,5,1))
            
            ######same code
            
            
            #NoData_cloud_mask = np.ma.masked_where(current_PIA==255,cloud_PIA)
            #ref_PIA_NoData = np.ma.compressed(NoData_ref_mask)
            
            
            bandas = ['B1', 'B2', 'B3', 'B4','B5', 'B7']
            lista_kl = []
            for i in os.listdir(ruta):
                banda = i[-6:-4]
                if banda in bandas:
                    raster = os.path.join(ruta, i)
                    #bandraster = gdal.Open(raster)
                    #data = bandraster.ReadAsArray()
                    with rasterio.open(raster) as src:
                        data = src.read()
                    #anadimos la distincion entre Fmask y BQA
                    if self.cloud_mask == 'Fmask':
                        print 'usando Fmask'
                        data2 = data[(erode == 1) & ((Fmask==1) | (((Fmask==0)) & (Hillshade<(np.percentile(Hillshade, 20)))))]
                        #gaps2 = gaps[((Fmask==1) | (((Fmask==0)) & (Hillshade<(np.percentile(Hillshade, 20)))))]
                        #data2 = data22[gaps2 == 8]

                    #else: Aqui iri al alternativa con Fmask, pero L7 no tiene banda de calidad, asi que no tiene sentido
                    #abria que poner la mascara del protocolo manual que hizo Javier Bustamante
                    print 'data 2 obtenido'
                    lista_kl.append(data2.min())#anadimos el valor minimo (podria ser perceniles) a la lista de kl
                    lista = sorted(data2.tolist())
                    print 'lista: ', lista[:10]
                    #nmask = (data2<lista[1000])#probar a coger los x valores mas bajos, a ver hasta cual aguanta bien
                    data3 = data2[:self.hist]
                    print 'data3: ', data3.min(), data3.max()

                    df = pandas.DataFrame(lista[:10000])
                    #plt.figure(); df.hist(figsize=(10,8), bins = 100)#incluir titulo y rotulos de ejes
                    plt.figure(); df.hist(figsize=(10,8), bins = 20, cumulative=False, color="Red"); 
                    plt.title(self.escena + '_gr_' + banda, fontsize = 18)
                    plt.xlabel("Pixel Value", fontsize=16)  
                    plt.ylabel("Count", fontsize=16)
                    path_rad = os.path.join(self.rad, self.escena)
                    if not os.path.exists(path_rad):
                        os.makedirs(path_rad)
                    name = os.path.join(path_rad, self.escena + '_gr_'+ banda.lower() + '.png')
                    plt.savefig(name)

            plt.close('all')
            print 'Histogramas generados'

        #Hasta aqui tenemos los histogramas generados y los valores minimos guardados en lista_kl, ahora 
        #debemos escribir los valores minimos de cada banda en el archivo kl.rad
            for i in os.listdir(self.rad):

                    if i.endswith('l7.rad'):

                        archivo = os.path.join(self.rad, i)
                        dictio = {5: lista_kl[0], 6: lista_kl[1], 7: lista_kl[2], 8: lista_kl[3], 9: lista_kl[4], 10: lista_kl[5]}

                        rad = open(archivo, 'r')
                        rad.seek(0)
                        lineas = rad.readlines()

                        for n, e in enumerate(lineas):
    
                            if n in dictio.keys():
                                print lineas[n]
                                lineas[n] = lineas[n].split('=')[0] + '=' + str(dictio[n]) + '\n'
                                print lineas[n]
                        rad.close()

                        f = open(archivo, 'w')
                        for linea in lineas:
                            f.write(linea)

                        f.close()

                        src = os.path.join(self.rad, i)
                        dst = os.path.join(path_rad, self.escena + '_kl.rad')
                        shutil.copy(src, dst)

            print 'modificados los metadatos del archivo kl_l7.rad\nProceso finalizado en ' + str(time.time()-t) + ' segundos'
        
        else:
            #self.hist == 200000
            print 'usando l5 o l7 pregapfill'
            bandas = ['B1', 'B2', 'B3', 'B4','B5', 'B7']
            lista_kl = []
            
            #vamos a necesitar un raster con la extension de la escena 202_34 para obtener el kl
            #como la extension de cada escena es distinta, debemos de tomar el shape de la escena
            #y pasarlo a raster con la extension de cada escena
            
            #obtenemos el extent de la escena del poly_shape
            wrs = r'C:\Protocolo\data\wrs_202_34.shp'
            raster_extent = r'C:\Protocolo\data\temp\extent.tif'
            source_ds = ogr.Open(shape)
            source_layer = source_ds.GetLayer()
            x_min, x_max, y_min, y_max = source_layer.GetExtent()
            extent = str(x_min) + ' ' + str(y_min) + ' ' + str(x_max) + ' ' + str(y_max)
            #ahora creamos el raster con la extension de la escena, tendra valor 0 
            #en todo lo que no sea el porpio marco oficial de la escena 202_34
            s = 'gdal_rasterize -a AREA -tr 30 30 -te {0} -ot Byte -l wrs_202_34 {1} {2}'.format(extent, wrs, raster_extent )
            cmd = s.split()
            print cmd
            proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            stdout,stderr=proc.communicate()
            exit_code=proc.wait()

            if exit_code: 
                raise RuntimeError(stderr)
            else:
                print stdout
                print 'raster extent generado'
            
            #ya tenemos el raster con el extent de la escena que estamos tratando, ahora pasamos a obtener los kl
            #abrimos el nuevo raster con el extent para usarlo como mascara
            with rasterio.open(raster_extent) as src:
                rsextent = src.read()
            #comenzamos a recorrer las bandas de la escena  
            for i in os.listdir(ruta):
                banda = i[-6:-4]
                if banda in bandas:
                    raster = os.path.join(ruta, i)
                    print raster
                    #bandraster = gdal.Open(raster)
                    #data = bandraster.ReadAsArray()
                    with rasterio.open(raster) as src:
                        data = src.read()
                        print 'data ' ,data.shape
                    #anadimos la distincion entre Fmask y BQA
                    if self.cloud_mask == 'Fmask':
                        print 'usando Fmask'
                        print 'FM ', Fmask.shape
                        print 'HS ', Hillshade.shape
                        print 'Banda ', data.shape
                        mask = data
                        mask[mask != 0] == 1
                        erodep = ndimage.grey_erosion(mask, size=(15,15,1))
                        data2 = data[((erodep != 0) & ((rsextent != 0) & (((Fmask==1) | (((Fmask==0)) & (Hillshade<(np.percentile(Hillshade, 20))))))))]
                        print 'data2_mean ', data2.mean(), ' data2_size', data2.size

                    #else: Aqui iri al alternativa con Fmask, pero L7 no tiene banda de calidad, asi que no tiene sentido
                    #abria que poner la mascara del protocolo manual que hizo Javier Bustamante
                    print 'data 2 obtenido'
                    lista_kl.append(data2.min())#anadimos el valor minimo (podria ser perceniles) a la lista de kl
                    lista = sorted(data2.tolist())
                    print 'lista: ', lista[:10]
                    #nmask = (data2<lista[1000])#probar a coger los x valores mas bajos, a ver hasta cual aguanta bien
                    #data3 = data2[:self.hist]
                    #print 'data3: ', data3.min(), data3.max()

                    df = pandas.DataFrame(lista[:self.hist])
                    #plt.figure(); df.hist(figsize=(10,8), bins = 100)#incluir titulo y rotulos de ejes
                    plt.figure(); df.hist(figsize=(10,8), bins = 20, cumulative=False, color="Red"); 
                    plt.title(self.escena + '_gr_' + banda, fontsize = 18)
                    plt.xlabel("Pixel Value", fontsize=16)  
                    plt.ylabel("Count", fontsize=16)
                    path_rad = os.path.join(self.rad, self.escena)
                    if not os.path.exists(path_rad):
                        os.makedirs(path_rad)
                    name = os.path.join(path_rad, self.escena + '_gr_'+ banda.lower() + '.png')
                    plt.savefig(name)

            plt.close('all')
            print 'Histogramas generados'

            #Hasta aqui tenemos los histogramas generados y los valores minimos guardados en lista_kl, ahora 
            #debemos escribir los valores minimos de cada banda en el archivo kl.rad
            for i in os.listdir(self.rad):

                if i.endswith('l7.rad'):

                    archivo = os.path.join(self.rad, i)
                    dictio = {5: lista_kl[0], 6: lista_kl[1], 7: lista_kl[2], 8: lista_kl[3], 9: lista_kl[4], 10: lista_kl[5]}

                    rad = open(archivo, 'r')
                    rad.seek(0)
                    lineas = rad.readlines()

                    for n, e in enumerate(lineas):

                        if n in dictio.keys():
                            print lineas[n]
                            lineas[n] = lineas[n].split('=')[0] + '=' + str(dictio[n]) + '\n'
                            print lineas[n]
                    rad.close()

                    f = open(archivo, 'w')
                    for linea in lineas:
                        f.write(linea)

                    f.close()

                    src = os.path.join(self.rad, i)
                    dst = os.path.join(path_rad, self.escena + '_kl.rad')
                    shutil.copy(src, dst)

            print 'modificados los metadatos del archivo kl_l7.rad\nProceso finalizado en ' + str(time.time()-t) + ' segundos'
        
        
    def remove_masks(self):
        
        '''-----\n
        Este metodo elimina la carpeta en la que hemos ido guardando las mascaras empleadas para obtener los kl y
        la cobertura de nubes en el Parque Nacional'''
        
        if self.sat == 'L7' and self.escena > '20030714':
            ruta = self.gapfill
        else:
            ruta = self.ruta_escena
        
        path_masks = os.path.join(ruta, 'masks')
        for i in os.listdir(path_masks):
            
            name = os.path.join(path_masks, i)
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)

        shutil.rmtree(path_masks)
        
        
    def reproject(self):
        
        '''-----\n
        Este metodo reproyecta los geotiff originales, tomando todos los parametros que necesita para la salida, 
        extent, SCR, etc. Al mismo tiempo los cambia a formato img + hdr'''
        
        if self.sat == 'L8':
            dgeo = {'B1': '_g_b1.img', 'B2': '_g_b2.img', 'B3': '_g_b3.img', 'B4': '_g_b4.img', 'B5': '_g_b5.img',\
             'B6': '_g_b6.img', 'B7': '_g_b7.img', 'B8': '_g_b8.img', 'B9': '_g_b9.img',\
           'B10': '_g_b10.img', 'B11': '_g_b11.img', 'BQA': '_g_bqa.img'}
        elif self.sat == 'L7':
            dgeo = {'B1': '_g_b1.img', 'B2': '_g_b2.img', 'B3': '_g_b3.img', 'B4': '_g_b4.img', 'B5': '_g_b5.img',\
             'B6_VCID_1': '_g_b6.img', 'B6_VCID_2': '_g_b9.img', 'B7': '_g_b7.img', 'B8': '_g_b8.img'}
        else:
            dgeo = {'B1': '_g_b1.img', 'B2': '_g_b2.img', 'B3': '_g_b3.img', 'B4': '_g_b4.img', 'B5': '_g_b5.img',\
             'B6': '_g_b6.img', 'B7': '_g_b7.img'}
            
        #cremos la carpeta con la ruta de destino
        destino = os.path.join(self.geo, self.escena)
        if not os.path.exists(destino):
            os.mkdir(destino)
        
        ti = time.time()
        #Entramos en el loop dentro de la carpeta y buscamos todos los archivos tipo .TIF
        
        if self.sat == 'L7' and self.escena > '20030714':
            ruta = self.gapfill
        else:
            ruta = self.ruta_escena
            
        for i in os.listdir(ruta):
            
            if i.endswith('.TIF'): 
                
                if not i.endswith('_Fmask.TIF'):
                    
                    t = time.time()
                    
                    banda = None
                    if len(i) == 28:
                        banda = i[-6:-4]
                    elif len(i) == 29:
                        banda = i[-7:-4]
                    else:
                        banda = i[-13:-4]
                    if banda in dgeo.keys():    
                        
                        raster = os.path.join(ruta, i)
                        salida = os.path.join(destino, self.escena + dgeo[banda])
                        cmd = ['gdalwarp', '-s_srs', '"+proj=utm +zone=29 +datum=wgs84 +units=m"', '-t_srs', '"+proj=utm +zone=30 +ellps=intl +towgs84=-84,-107,-120,0,0,0,0 +units=m +no_defs"', '-r', 'cubic', '-te', '78000 4036980 340020 4269000', '-tr', '30 30', '-of', 'ENVI']
                        cmd.append(raster)
                        cmd.append(salida)
                        cmd.append('--config GDAL_CACHEMAX 8000 -wm 8000')
                        cmd.append('--config GDAL_NUM_THREADS ALL_CPUS')
                        warp = (" ").join(cmd)
                        subprocess.call(warp)

                        print 'banda '+ str(i) + ' finalizada en  ' + str(time.time()-t)
                
                else: #anadiendo la posibilidad de mascara de calidad
                    print 'nubes: ', i
                    path_nor = os.path.join(self.nor, self.escena)
                    if not os.path.exists(path_nor):
                        os.makedirs(path_nor)

                    t = time.time()
                    print "Reproyectando " + i

                    salida = os.path.join(path_nor, self.escena + '_Fmask.img')
                    raster = os.path.join(ruta, i)
                    cmd = ['gdalwarp', '-s_srs', '"+proj=utm +zone=29 +datum=wgs84 +units=m"', '-t_srs', '"+proj=utm +zone=30 +ellps=intl +towgs84=-84,-107,-120,0,0,0,0 +units=m +no_defs"', '-te', '78000 4036980 340020 4269000', '-tr', '30 30', '-of', 'ENVI', '-dstnodata', '255']
                    cmd.append(raster)
                    cmd.append(salida)
                    cmd.append('--config GDAL_CACHEMAX 8000 -wm 8000')
                    cmd.append('--config GDAL_NUM_THREADS ALL_CPUS')
                    warp = (" ").join(cmd)
                    subprocess.call(warp)

                    print 'banda '+ str(i) + ' finalizada en  ' + str(time.time()-t)
                         
            elif i.endswith('MTLFmask.img'): 
                #Cona la Fmask elegimos la reproyeccion por Vecinos Naturales ya que de otro modo nos altera los valores de NoData
                path_nor = os.path.join(self.nor, self.escena)
                if not os.path.exists(path_nor):
                    os.makedirs(path_nor)
                    
                t = time.time()
                print "Reproyectando " + i
                    
                salida = os.path.join(path_nor, self.escena + '_Fmask.img')
                raster = os.path.join(ruta, i)
                cmd = ['gdalwarp', '-s_srs', '"+proj=utm +zone=29 +datum=wgs84 +units=m"', '-t_srs', '"+proj=utm +zone=30 +ellps=intl +towgs84=-84,-107,-120,0,0,0,0 +units=m +no_defs"', '-te', '78000 4036980 340020 4269000', '-tr', '30 30', '-of', 'ENVI', '-dstnodata', '255']
                cmd.append(raster)
                cmd.append(salida)
                cmd.append('--config GDAL_CACHEMAX 8000 -wm 8000')
                cmd.append('--config GDAL_NUM_THREADS ALL_CPUS')
                warp = (" ").join(cmd)
                subprocess.call(warp)
                
                print 'banda '+ str(i) + ' finalizada en  ' + str(time.time()-t)
                
        print "Reproyeccion completa realizada en " + str((time.time()-ti)/60) + " minutos"
        
        
    def copyDocG(self):
        
        '''-----\n
        Este metodo copia los doc y el rel generados por Miramon al importar la imagen y los pasa a geo'''

        rutageo = os.path.join(self.geo, self.escena)
        for i in os.listdir(self.mimport):
    
            if self.sat == 'L8':
            
                d = {'B1-CA': '_g_b1', 'B10-LWIR1': '_g_b10', 'B11-LWIR2': '_g_b11', 'B2-B': '_g_b2', 'B3-G': '_g_b3', 'B4-R': '_g_b4', 'B5-NIR': '_g_b5', 'B6-SWIR1': '_g_b6', 'B7-SWIR2': '_g_b7',\
                'B8-PAN': '_g_b8', 'B9-CI': '_g_b9', 'BQA-CirrusConfidence': '_g_BQA-Cirrus', 'BQA-CloudConfidence': '_g_BQA-Cloud', 'BQA-DesignatedFill': '_g_BQA-DFill',\
                'BQA-SnowIceConfidence': '_g_BQA-SnowIce', 'BQA-TerrainOcclusion': '_g_BQA-Terrain', 'BQA-WaterConfidence': '_g_BQA-Water'}
            
            elif self.sat == 'L7':
                
                d = {'B1-B': '_g_b1', 'B2-G': '_g_b2', 'B3-R': '_g_b3', 'B4-IRp': '_g_b4', 'B5-IRm1': '_g_b5', 'B6-IRt': '_g_b6', 'B7-IRm2': '_g_b7',\
                'B8-PAN': '_g_b8', 'B9-IRt_HG': '_g_b9'}
                
            else:
                
                d = {'B1-B': '_g_b1', 'B2-G': '_g_b2', 'B3-R': '_g_b3', 'B4-IRp': '_g_b4', 'B5-IRm1': '_g_b5', 'B6-IRt': '_g_b6', \
                     'B7-IRm2': '_g_b7'}
                
            if i.endswith('.doc'):
                
                number = i[20:-7]
                print number
                key = d[number]
                print key
                src = os.path.join(self.mimport, i)
                dst = os.path.join(rutageo, self.escena + key + '.doc')
                shutil.copy(src, dst)
                
            elif i.endswith('.rel'):
                
                src = os.path.join(self.mimport, i)
                dst = os.path.join(rutageo, self.escena + '_g_' + i[-6:])
                shutil.copy(src, dst)
                
            else: continue
                
        print 'Archivos doc y rel copiados a geo'
                
    def modifyDocG(self):
        
        '''-----\n
        Este metodo edita los doc copiados a geo para que tenga los valores correctos'''
        
        ruta = os.path.join(self.geo, self.escena)
        print ruta
        for i in os.listdir(ruta):
        
            if i.endswith('.doc'):

                archivo = os.path.join(ruta, i)

                doc = open(archivo, 'r')
                doc.seek(0)
                lineas = doc.readlines()

                for l in range(len(lineas)):

                    if lineas[l].startswith('columns'):
                        lineas[l] = 'columns     : 8734\n'
                    elif lineas[l].startswith('rows'):
                        lineas[l] = 'rows        : 7734\n'
                    elif lineas[l].startswith('min. X'):
                        lineas[l] = 'min. X      : 78000.0000000000\n'
                    elif lineas[l].startswith('max. X'):
                        lineas[l] = 'max. X      : 340020.000000000\n'
                    elif lineas[l].startswith('min. Y'):
                        lineas[l] = 'min. Y      : 4036980.00000000\n'
                    elif lineas[l].startswith('max. Y'):
                        lineas[l] = 'max. Y      : 4269000.00000000\n'
                    elif lineas[l].startswith('ref. system'):
                        lineas[l] = 'ref. system : UTM-30N-PS\n'
                    else: continue

                doc.close()

                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                print 'modificados los metadatos de ', i
                
                
    def modifyRelG(self):
        
        '''-----\n
        Este metodo modifica el rel de geo para que tenga los valores correctos'''
        
        process = '\n[QUALITY:LINEAGE:PROCESS2]\nnOrganismes=1\nhistory=reproyeccion\npurpose=reproyeccion por convolucion cubica\ndate=' + str(time.strftime("%Y%m%d %H%M%S00")) + '\n'
        tech = '\n[QUALITY:LINEAGE:PROCESS2:ORGANISME_1]\nIndividualName=Auto Protocol Proudly made by Diego Garcia Diaz\nPositionName=Tecnico LAST\nOrganisationName=(CSIC) LAST-EBD (APP)\n'
        pro = process + tech + '\n'
        
        ruta = os.path.join(self.geo, self.escena)
        for i in os.listdir(ruta):
            if i.endswith('rel'):
                rel_file = os.path.join(ruta, i)
        
        rel = open(rel_file, 'r')
        lineas = rel.readlines()
        
        if self.sat == 'L8':
        
            dgeo = {'B1-CA': '_g_b1', 'B10-LWIR1': '_g_b10', 'B11-LWIR2': '_g_b11', 'B2-B': '_g_b2', 'B3-G': '_g_b3', 'B4-R': '_g_b4', 'B5-NIR': '_g_b5', 'B6-SWIR1': '_g_b6', 'B7-SWIR2': '_g_b7',\
                    'B8-PAN': '_g_b8', 'B9-CI': '_g_b9', 'BQA-CirrusConfidence': '_g_BQA-Cirrus', 'BQA-CloudConfidence': '_g_BQA-Cloud', 'BQA-DesignatedFill': '_g_BQA-DFill',\
                    'BQA-SnowIceConfidence': '_g_BQA-SnowIce', 'BQA-TerrainOcclusion': '_g_BQA-Terrain', 'BQA-WaterConfidence': '_g_BQA-Water'}

            for l in range(len(lineas)):

                if lineas[l].rstrip() == '[EXTENT]':
                    lineas[l-1] = pro
                elif lineas[l].startswith('FileIdentifier'):
                    lineas[l] = 'FileIdentifier='+ self.escena + '_g_' + lineas[l][-9:]
                elif lineas[l].startswith('IndividualName'):
                    lineas[l] = 'IndividualName=Digd_Geo\n'
                elif lineas[l].startswith('PositionName'):
                    lineas[l] = 'PositionName=Tecnico GIS-RS LAST-EBD\n'
                elif lineas[l].startswith('columns'):
                    lineas[l] = 'columns=8734\n'
                elif lineas[l].startswith('rows'):
                    lineas[l] = 'rows=7734\n'
                elif lineas[l].startswith('MinX'):
                    lineas[l] = 'MinX=78000\n'
                elif lineas[l].startswith('MaxX'):
                    lineas[l] = 'MaxX=340020\n'
                elif lineas[l].startswith('MinY'):
                    lineas[l] = 'MinY=4036980\n'
                elif lineas[l].startswith('MaxY'):
                    lineas[l] = 'MaxY=4269000\n'
                elif lineas[l].startswith('max. Y'):
                    lineas[l] = 'MinY=4036980\n'  
                elif lineas[l].startswith('HorizontalSystemIdentifier'):
                    lineas[l] = 'HorizontalSystemIdentifier=UTM-30N-PS\n'
                elif lineas[l].startswith('IndexsNomsCamps'):
                    lineas[l] = 'IndexsNomsCamps=1-CA,2-B,3-G,4-R,5-NIR,6-SWIR1,7-SWIR2,9-CI\n'
                elif lineas[l].startswith('NomFitxer=LC8_202034'):
                    bandname = lineas[l][30:-8]
                    lineas[l] = 'NomFitxer='+self.escena+dgeo[bandname]+'.img\n'
                elif lineas[l] == '[ATTRIBUTE_DATA:8-PAN]\n':
                    start_b8 = l
                elif lineas[l] == '[ATTRIBUTE_DATA:9-CI]\n':
                    end_b8 = l
                elif lineas[l].startswith('NomCamp_10-LWIR1=10-LWIR1'):
                    start_band_name = l
                elif lineas[l].startswith('NomCamp_17=QA-CloudConfidence'):
                    end_band_name = l+1
                elif lineas[l].startswith('[ATTRIBUTE_DATA:10-LWIR1]'):
                    start_end = l
                else: continue

            rel.close()

            new_list = lineas[:start_band_name]+lineas[end_band_name:start_b8]+lineas[end_b8:start_end]
            new_list.remove('NomCamp_8-PAN=8-PAN\n')
            
            f = open(rel_file, 'w')
            for linea in new_list:
                f.write(linea)

            f.close()
            
        elif self.sat == 'L7': 
        
        
            dgeo = {'B1-B': '_g_b1', 'B2-G': '_g_b2', 'B3-R': '_g_b3', 'B4-IRp': '_g_b4', 'B5-IRm1': '_g_b5', 'B6-IRt': '_g_b6', 'B7-IRm2': '_g_b7',\
                'B8-PAN': '_g_b8', 'B9-IRt_HG': '_g_b9'}
            
            for l in range(len(lineas)):

                if lineas[l].rstrip() == '[EXTENT]':
                    lineas[l-1] = pro
                elif lineas[l].startswith('FileIdentifier'):
                    lineas[l] = 'FileIdentifier='+ self.escena + '_g_' + lineas[l][-9:]
                elif lineas[l].startswith('IndividualName'):
                    lineas[l] = 'IndividualName=Digd_Geo\n'
                elif lineas[l].startswith('PositionName'):
                    lineas[l] = 'PositionName=Tecnico GIS-RS LAST-EBD\n'
                elif lineas[l].startswith('columns'):
                    lineas[l] = 'columns=8734\n'
                elif lineas[l].startswith('rows'):
                    lineas[l] = 'rows=7734\n'
                elif lineas[l].startswith('MinX'):
                    lineas[l] = 'MinX=78000\n'
                elif lineas[l].startswith('MaxX'):
                    lineas[l] = 'MaxX=340020\n'
                elif lineas[l].startswith('MinY'):
                    lineas[l] = 'MinY=4036980\n'
                elif lineas[l].startswith('MaxY'):
                    lineas[l] = 'MaxY=4269000\n'
                elif lineas[l].startswith('max. Y'):
                    lineas[l] = 'MinY=4036980\n'  
                elif lineas[l].startswith('HorizontalSystemIdentifier'):
                    lineas[l] = 'HorizontalSystemIdentifier=UTM-30N-PS\n'
                elif lineas[l].startswith('IndexsNomsCamps'):
                    lineas[l] = 'IndexsNomsCamps=1-B,2-G,3-R,4-IRp,5-IRm1,7-IRm2\n'
                elif lineas[l].startswith('NomFitxer=LE7_202034'):
                    bandname = lineas[l][30:-8]
                    lineas[l] = 'NomFitxer='+self.escena+dgeo[bandname]+'.img\n'
                elif lineas[l] == '[ATTRIBUTE_DATA:6-IRt]\n':
                    start_b6 = l-1
                elif lineas[l] == '[ATTRIBUTE_DATA:7-IRm2]\n':
                    start_b7 = l
                elif lineas[l] == ('[ATTRIBUTE_DATA:8-PAN]\n'):
                    start_b8 = l
                else: continue

            rel.close()

            new_list = lineas[:start_b6]+lineas[start_b7:start_b8]
            new_list.remove('NomCamp_6-IRt=6-IRt\n')
            new_list.remove('NomCamp_9-IRt_HG=9-IRt_HG\n')
            new_list.remove('NomCamp_8-PAN=8-PAN\n')

            f = open(rel_file, 'w')
            for linea in new_list:
                f.write(linea)

            f.close()
        

        else: 
        
        
            dgeo = {'B1-B': '_g_b1', 'B2-G': '_g_b2', 'B3-R': '_g_b3', 'B4-IRp': '_g_b4', 'B5-IRm1': '_g_b5', 'B6-IRt': '_g_b6', 'B7-IRm2': '_g_b7'}
            
            for l in range(len(lineas)):

                if lineas[l].rstrip() == '[EXTENT]':
                    lineas[l-1] = pro
                elif lineas[l].startswith('FileIdentifier'):
                    lineas[l] = 'FileIdentifier='+ self.escena + '_g_' + lineas[l][-9:]
                elif lineas[l].startswith('IndividualName'):
                    lineas[l] = 'IndividualName=Digd_Geo\n'
                elif lineas[l].startswith('PositionName'):
                    lineas[l] = 'PositionName=Tecnico GIS-RS LAST-EBD\n'
                elif lineas[l].startswith('columns'):
                    lineas[l] = 'columns=8734\n'
                elif lineas[l].startswith('rows'):
                    lineas[l] = 'rows=7734\n'
                elif lineas[l].startswith('MinX'):
                    lineas[l] = 'MinX=78000\n'
                elif lineas[l].startswith('MaxX'):
                    lineas[l] = 'MaxX=340020\n'
                elif lineas[l].startswith('MinY'):
                    lineas[l] = 'MinY=4036980\n'
                elif lineas[l].startswith('MaxY'):
                    lineas[l] = 'MaxY=4269000\n'
                elif lineas[l].startswith('max. Y'):
                    lineas[l] = 'MinY=4036980\n'  
                elif lineas[l].startswith('HorizontalSystemIdentifier'):
                    lineas[l] = 'HorizontalSystemIdentifier=UTM-30N-PS\n'
                elif lineas[l].startswith('IndexsNomsCamps'):
                    lineas[l] = 'IndexsNomsCamps=1-B,2-G,3-R,4-IRp,5-IRm1,7-IRm2\n'
                elif lineas[l].startswith('NomFitxer=LT5_202034'):
                    bandname = lineas[l][30:-8]
                    lineas[l] = 'NomFitxer='+self.escena+dgeo[bandname]+'.img\n'
                elif lineas[l] == '[ATTRIBUTE_DATA:6-IRt]\n':
                    start_b6 = l-1
                elif lineas[l] == '[ATTRIBUTE_DATA:7-IRm2]\n':
                    start_b7 = l
                else: continue

            rel.close()

            new_list = lineas[:start_b6]+lineas[start_b7:]
            new_list.remove('NomCamp_6-IRt=6-IRt\n')

            f = open(rel_file, 'w')
            for linea in new_list:
                f.write(linea)

            f.close()
            
            
    def copy_files_GR(self):
        
        '''-----\n
        Este metodo copia las bandas de 1 a 9 de geo a rad, para proceder a la correccion radiometrica'''

        lista_bandas = ['b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b9']

        path_escena_geo =  os.path.join(self.geo, self.escena)
        path_escena_rad =  os.path.join(self.rad, self.escena)
        if not os.path.exists(path_escena_rad):
            os.makedirs(path_escena_rad)

        for i in os.listdir(path_escena_geo):

            banda = i[-6:-4]

            if banda in lista_bandas:

                src = os.path.join(path_escena_geo, i)
                dst = os.path.join(path_escena_rad, i)   
                shutil.copy(src, dst)

            elif i.endswith('.rel'):

                src = os.path.join(path_escena_geo, i)
                dst = os.path.join(path_escena_rad, i)
                shutil.copy(src, dst)

            else: continue

        print 'Archivos copiados y renombrados a Rad'
           
                
    def createR_bat(self):
        
        '''-----\n
        Este metodo crea el bat para realizar la correcion radiometrica'''

        #Incluimos reflectividades por arriba y por debajo de 100 y 0
        path_escena_rad = os.path.join(self.rad, self.escena)
        corrad = 'C:\MiraMon\CORRAD'
        num1 = '1'
        dtm = os.path.join(self.rad, 'sindato.img')
        if self.sat == 'L8':
            kl = os.path.join(self.rad, 'kl_l8.rad')
        else:
            kl = os.path.join(self.rad, 'kl_l7.rad')
        #REF_SUP y REF_INF es xa el ajuste o no a 0-100, mirar si se quiere o no
        string = '/MULTIBANDA /CONSERVAR_MDT /LIMIT_LAMBERT=73.000000 /REF_SUP_100 /REF_INF_0 /DT=c:\MiraMon'

        for i in os.listdir(os.path.join(self.rad, self.escena)):
            if i.endswith('b1.img'):
                banda1 = os.path.join(path_escena_rad, i)
            else: continue

        lista = [corrad, num1, banda1, path_escena_rad,  dtm, kl, string]
        print lista

        batline = (" ").join(lista)

        pr = open(self.bat2, 'w')
        pr.write(batline)
        pr.close()


    def callR_bat(self):

        '''-----\n
        Este metodo ejecuta el bat que realiza la correcion radiometrica'''
        
        ti = time.time()
        print 'Llamando a Miramon... Miramon!!!!!!'
        a = os.system(self.bat2)
        a
        if a == 0:
            print "Escena corregida con exito en " + str(time.time()-ti) + " segundos"
        else:
            print "No se pudo realizar la correccion de la escena"
        #borramos el archivo bat creado para la importacion de la escena, una vez se ha importado esta
        os.remove(self.bat2)
        
        
    def cleanR(self):
        
        '''-----\n
        Este metodo borra los archivos copiados de geo, de modo que nos quedamos solo con los hdr y los img y doc generado 
        por el Corrad, junto con los png de los histogramas'''         
        
        path_escena_rad = os.path.join(self.rad, self.escena)
        
        #Copiamos el rel tal y como sale del Corrad
        for i in os.listdir(path_escena_rad):
            if i.startswith('r_') and i.endswith('.rel'):
                rel = os.path.join(path_escena_rad, i)
                rel_txt = os.path.join(path_escena_rad, 'rel_original_values.txt')
                shutil.copy(rel, rel_txt)                         
        #Borramos los archivos que no hacen falta
        for i in os.listdir(path_escena_rad):
            if not i.startswith('r_'):
                if not i.endswith('.hdr'):
                    if not i.endswith('.png'):
                        if not i.endswith('.rad'):
                            if not i.endswith('.txt'):
                                os.remove(os.path.join(path_escena_rad, i))
            elif i.startswith('r_'):
                src = os.path.join(path_escena_rad, i)
                dst = os.path.join(path_escena_rad, i[2:].replace('_g_', '_gr_'))
                os.rename(src, dst)
                
        #hdrs
        for i in os.listdir(path_escena_rad):
            if i.endswith('.hdr'):
                src = os.path.join(path_escena_rad, i)
                dst = os.path.join(path_escena_rad, i.replace('_g_', '_gr_'))
                #dst = os.path.join(path_escena_rad, i[:21]+'r'+i[-7:])
                os.rename(src, dst)
            
    
    def correct_sup_inf(self):
        
        '''-----\n
        Este metodo soluciona el problema de los pixeles con alta y baja reflectividad, llevando los bajos a valor 0 
        y los altos a 100. La salida sigue siendo en float32 (reales entre 0.0 y 100.0) con el nodata en 255'''
        
        path_escena_rad = os.path.join(self.rad, self.escena)
        for i in os.listdir(path_escena_rad):
       
            if i.endswith('.img'):
                
                banda = os.path.join(path_escena_rad, i)
                outfile = os.path.join(path_escena_rad, 'crt_' + i)
                
                with rasterio.drivers():
                    with rasterio.open(banda) as src:
                        rs = src.read()
                        mini = (rs == rs.min())
                        min_msk = (rs>rs.min()) & (rs<=0)
                        max_msk = (rs>=100)
                        rs[min_msk] = 0
                        rs[max_msk] = 100.0
                        rs[mini] = 255 #el valor que tendra el nodata
                        
                        profile = src.meta
                        profile.update(dtype=rasterio.float32)

                        with rasterio.open(outfile, 'w', **profile) as dst:
                            dst.write(rs.astype(rasterio.float32))
                            
    def clean_correct_R(self):
        
        '''-----\n
        Este metodo borra los archivos resultantes del Corrad antes de hacer 
        la correccion de reflectividades altas y bajas''' 
        
        path_escena_rad = os.path.join(self.rad, self.escena)
        for i in os.listdir(path_escena_rad):
            if (i.endswith('.img')| i.endswith('.hdr')) and not i.startswith('crt'):
                os.remove(os.path.join(path_escena_rad, i))
                
        for i in os.listdir(path_escena_rad):
            if i.endswith('aux.xml'):
                os.remove(os.path.join(path_escena_rad, i))
        
        for i in os.listdir(path_escena_rad):
            if i.endswith('.img')| i.endswith('.hdr'):
                src = os.path.join(path_escena_rad, i)
                dst = os.path.join(path_escena_rad, i[4:])
                os.rename(src,dst)
                
                
    def modify_hdr_rad(self): #QUITAR DEL CORRAD. En principio ya no va a hacer falta, en todo caso se podria usar xa insertar el IgnoreValue
        
        '''-----\nEste metodo edita los hdr para que tengan el valor correcto (FLOAT) para poder ser entendidos por GDAL.
        Hay que ver si hay que establecer primero el valor como No Data'''
                
        path_escena_rad = os.path.join(self.rad, self.escena)
        for i in os.listdir(path_escena_rad):
        
            if i.endswith('.hdr'):

                archivo = os.path.join(path_escena_rad, i)
                hdr = open(archivo, 'r')
                hdr.seek(0)
                lineas = hdr.readlines()
                for l in range(len(lineas)):
                    if l == 8:
                        lineas[l] = 'data type = 4\n'
                lineas.append('data ignore value = -3.40282347e+38') 
                 
                hdr.close()

                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                print 'modificados los metadatos de ', i
                
    def modify_hdr_rad_255(self): 
        
        '''-----\n
        Este metodo edita los hdr para que tengan el valor correcto (FLOAT) para poder ser entendidos por GDAL.
        Hay que ver si hay que establecer primero el valor como No Data'''
                
        path_escena_rad = os.path.join(self.rad, self.escena)
        for i in os.listdir(path_escena_rad):
        
            if i.endswith('.hdr'):

                archivo = os.path.join(path_escena_rad, i)
                hdr = open(archivo, 'r')
                hdr.seek(0)
                lineas = hdr.readlines()
                for l in range(len(lineas)):
                    if l == 8:
                        lineas[l] = 'data type = 4\n'
                lineas.append('data ignore value = 255') 
                 
                hdr.close()

                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                print 'modificados los metadatos de ', i
                
    def translate_bytes_gdal(self):
    
        '''-----\n
        Este metodo hace la conversion de reales (float32) a byte'''
        
        path_escena_rad = os.path.join(self.rad, self.escena)
        path_escena_rad_byte = os.path.join(path_escena_rad, 'byte')
        if not os.path.exists(path_escena_rad_byte):
            os.makedirs(path_escena_rad_byte)
        
        cmd = "gdal_translate -ot Byte -of ENVI -scale 0 100 0 254 -a_nodata 255 --config GDAL_CACHEMAX 8000 --config GDAL_NUM_THREADS ALL_CPUS"
        
        for i in os.listdir(path_escena_rad):

            if i.endswith('img'):

                input_rs = os.path.join(path_escena_rad, i)
                output_rs = os.path.join(path_escena_rad_byte, i)

                lst = cmd.split()
                lst.append(input_rs)
                lst.append(output_rs)

                proc = subprocess.Popen(lst,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                stdout,stderr=proc.communicate()
                exit_code=proc.wait()

                if exit_code: 
                    raise RuntimeError(stderr)
                else: 
                    print stdout 
                
           
    def modifyRelRad(self):
        
        '''-----\n
        Este metodo modifica el rel de rad para que tenga los valores correctos'''
        
        path_geo = os.path.join(self.geo, self.escena)
        path_rad = os.path.join(self.rad, self.escena)
        for i in os.listdir(path_geo):
            if i.endswith('rel'):
                rel_file_geo = os.path.join(path_geo, i)
    
        rel_geo = open(rel_file_geo, 'r')
        lineasgeo = rel_geo.readlines()
        for i in range(len(lineasgeo)):
            if lineasgeo[i] == '[QUALITY:LINEAGE:PROCESS1]\n':
                start = i
                end = start + 21

        pro = lineasgeo[start:end]         
        pros = '\n'+''.join(pro)

        for i in os.listdir(path_rad):
            if i.endswith('rel'):
                rel_file = os.path.join(path_rad, i)

        for line in fileinput.input(rel_file, inplace = 1): 
            print line.replace("PROCESS1", "PROCESS3"),
        for line in fileinput.input(rel_file, inplace = 1): 
            print line.replace("-3.4028235E+38", "255"),
        for line in fileinput.input(rel_file, inplace = 1): 
            print line.replace("%", "Refs(%)*254"),
        for line in fileinput.input(rel_file, inplace = 1): 
            print line.replace("processes=1", "processes=1,2,3"),


        rel = open(rel_file, 'r')
        lineas = rel.readlines()

        drad = {'b1': '_gr_b1.img', 'b2': '_gr_b2.img', 'b3': '_gr_b3.img', 'b4': '_gr_b4.img', 'b5': '_gr_b5.img','b6': '_gr_b6.img', 'b7': '_gr_b7.img', 'b8': '_gr_b8.img', 'b9': '_gr_b9.img'}

        for l in range(len(lineas)):

            if lineas[l].startswith('NomFitxer=r_'):
                bandname = lineas[l][-7:-5]
                lineas[l] = lineas[l][:10] + self.escena + drad[bandname]+'\n'
            elif lineas[l] == 'resolution=30\n':
                pos = l+1
            elif lineas[l].startswith('TipusCompressio'):
                lineas[l] = 'TipusCompressio=byte\n'
            elif lineas[l].startswith('ToneGradation'):
                lineas[l]='ToneGradation=255\n'            
            elif lineas[l].startswith('BitsPerValue'):
                lineas[l]='BitsPerValue=8\n'
            elif lineas[l].startswith('min='):
                lineas[l]='min=0\n'
            elif lineas[l].startswith('max='):
                lineas[l]='max=254\n'
            
        lineas.insert(pos, pros)
        rel.close()

        f = open(rel_file, 'w')
        for linea in lineas:
            f.write(linea)

        f.close()
        
        
    def re_clean_R(self):
        
        '''-----\n
        Este metodo borra las bandas procedentes de la primera correcion de las bandas en float32
        (para solucionar los valores de altas y bajas reflectividades).Se borran los img y hdr de la
        escena en byte, y se copian desde byte las bandas ya reescaladas, finalmente se borra la carpeta byte'''
        
        path_rad = os.path.join(self.rad, self.escena)
        path_rad_byte = os.path.join(path_rad, 'byte')
        
        #borramos los img y hdr reclasificados pero aun en porcentaje
        for i in os.listdir(path_rad):

            if i.endswith('.img') or i.endswith('hdr'):
                files = os.path.join(path_rad, i)
                os.remove(files)
            #else: continue
        
        #copiamos los hdr y los img de byte a la  carpeta de la escena en rad
        for i in os.listdir(path_rad_byte):

            if i.endswith('.img') or i.endswith('hdr'):
                src = os.path.join(path_rad_byte, i)
                dst = os.path.join(path_rad, i)
                os.rename(src, dst)
            #else: continue
                                
        #borramos la carpeta byte con los xml que quedan en ella
        for i in os.listdir(path_rad):
            fold = os.path.join(path_rad, i)
            if os.path.isdir(fold):
                shutil.rmtree(fold)
            
                
    def modifyDocR(self):
        
        '''-----\n
        Este metodo edita los doc de rad para que tengan los valores correctos'''
        
        path_rad = os.path.join(self.rad, self.escena)
                                
        for i in os.listdir(path_rad):
        
            if i.endswith('.doc'):

                archivo = os.path.join(path_rad, i)

                doc = open(archivo, 'r')
                doc.seek(0)
                lineas = doc.readlines()

                for l in range(len(lineas)):

                    if lineas[l].startswith('data type'):
                        lineas[l] = 'data type   : byte\n'
                    elif lineas[l].startswith('value units'):
                        lineas[l] = 'value units : Refs(%)*254\n'
                    elif lineas[l].startswith('flag value'):
                        lineas[l] = 'flag value  : 255\n'
                    elif lineas[l].startswith('min. value'):
                        lineas[l] = 'min. value  : 0\n'
                    elif lineas[l].startswith('max. value'):
                        lineas[l] = 'max. value  : 254\n'
                    else: continue

                doc.close()

                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                print 'modificados los metadatos de ', i
                                
                                
    def normalize(self):
        
        '''-----\n
        Este metodo controlo el flujo de la normalizacion, si no se llegan a obtener los coeficientes (R>0.85 y N_Pixeles >= 10,
        va pasando hacia el siguiente nivel, hasta que se logran obtener esos valores o hasta que se llega al ultimo paso)'''
        
        path_rad_escena = os.path.join(self.rad, self.escena)
                
        bandasl8 = ['b2', 'b3', 'b4', 'b5', 'b6', 'b7']
        bandasl7 = ['b1', 'b2', 'b3', 'b4', 'b5', 'b7']
        
        if self.sat == 'L7' or self.sat == 'L5':
            print 'landsat 5-7\n'
            lstbandas = bandasl7
        else:
            print 'landsat 8\n'
            lstbandas = bandasl8
        
        for i in os.listdir(path_rad_escena):
            
            banda = os.path.join(path_rad_escena, i)
            banda_num = banda[-6:-4]
            if banda_num in lstbandas and i.endswith('.img'):
                
                print banda, ' desde normalize'
                self.nor1(banda, self.noequilibrado)
                #Esto es un poco feo, pero funciona. Probar a hacerlo con una lista de funciones
                if banda_num not in self.parametrosnor.keys():
                    self.iter = 1
                    self.iter += 1
                    self.nor1(banda, self.noequilibrado, std = 22)
                    if banda_num not in self.parametrosnor.keys():
                        self.iter += 1
                        self.nor1(banda, self.equilibrado)
                        if banda_num not in self.parametrosnor.keys():
                            self.iter += 1
                            self.nor1(banda, self.equilibrado, std = 22)
                            if banda_num not in self.parametrosnor.keys():
                                self.iter += 1
                                self.nor1(banda, self.noequilibrado, std = 33,)
                                if banda_num not in self.parametrosnor.keys():
                                    self.iter += 1
                                    self.nor1(banda, self.noequilibrado, std = 33)
                                else:
                                    print 'No se ha podido normalizar la banda ', banda_num
                                    
            #Una vez acabados los bucles guardamos los coeficientes en un txt. Redundante pero asi hay 
            #que hacerlo porque quiere David
            path_nor = os.path.join(self.nor, self.escena)
            if not os.path.exists(path_nor):
                os.makedirs(path_nor)
            arc = os.path.join(path_nor, 'coeficientes.txt')
            f = open(arc, 'w')
            for i in sorted(self.parametrosnor.items()):
                f.write(str(i)+'\n')
            f.close()  
            
            #Insertamos los datos en la MongoDB (que es lo que mola, y no tanto txt ;))
            connection = pymongo.MongoClient("mongodb://localhost")
            db=connection.teledeteccion
            landsat = db.landsat

            try:

                landsat.update_one({'_id':self.escena}, {'$set':{'Info.Pasos.nor': {'Normalize': 'True', 'Nor-Values': self.parametrosnor, 'Fecha': datetime.now()}}})

            except Exception as e:
                print "Unexpected error:", type(e), e
                
    def nor1(self, banda, mascara, std = 11):
        
        '''-----\n
        Este metodo busca obtiene los coeficientes necesarios para llevar a cabo la normalizacion,
        tanto en nor1 como en nor1bis'''

        print 'comenzando nor1'
        
        #Ruta a las bandas usadas para normalizar
        ref = os.path.join(self.data, '20020718l7etm202_34')
        path_b1 = os.path.join(ref, '20020718l7etm202_34_grn1_b1.img')
        path_b2 = os.path.join(ref, '20020718l7etm202_34_grn1_b2.img')
        path_b3 = os.path.join(ref, '20020718l7etm202_34_grn1_b3.img')
        path_b4 = os.path.join(ref, '20020718l7etm202_34_grn1_b4.img')
        path_b5 = os.path.join(ref, '20020718l7etm202_34_grn1_b5.img')
        path_b7 = os.path.join(ref, '20020718l7etm202_34_grn1_b7.img')
        
        dnorbandasl8 = {'b2': path_b1, 'b3': path_b2, 'b4': path_b3, 'b5': path_b4, 'b6': path_b5, 'b7': path_b7}
        dnorbandasl7 = {'b1': path_b1, 'b2': path_b2, 'b3': path_b3, 'b4': path_b4, 'b5': path_b5, 'b7': path_b7}
        
        if self.sat == 'L7' or self.sat == 'L5':
            dnorbandas = dnorbandasl7
        else:
            dnorbandas = dnorbandasl8
            
        path_nor = os.path.join(self.nor, self.escena)
        for i in os.listdir(path_nor):
            
            if i.endswith('Fmask.img'):
                mask_nubes = os.path.join(path_nor, i)
                print 'Mascara de nubes: ', mask_nubes
                    
        if mascara == self.noequilibrado:
            poly_inv_tipo = os.path.join(self.data, 'pol_inv_tipo.img')
        else:
            poly_inv_tipo = os.path.join(self.data, 'pol_inv_2_tipo.img')

        print 'mascara: ', mascara
        
        with rasterio.open(mascara) as src:
            mask1 = src.read()
        with rasterio.open(mask_nubes) as src:
            cloud = src.read()
            #ahora pasamos el array a 1 (nubes) y 0 (resto) para evitar problemas con Fmask-BQA
            if self.cloud_mask == 'Fmask':
                
                cloud[(cloud!=2)|(cloud!=4)] = 0
                cloud[(cloud==2)|(cloud==4)] = 1
            
        with rasterio.open(poly_inv_tipo) as src:
            pias = src.read()

        banda_num = banda[-6:-4]
        print banda_num
        if banda_num in dnorbandas.keys():
            with rasterio.open(banda) as src:
                current = src.read()
            #Aqui con el diccionario nos aseguramos de que estamos comparando cada banda con su homologa del 20020718
            with rasterio.open(dnorbandas[banda_num]) as src:
                ref = src.read()
            #Ya tenemos todas las bandas de la imagen actual y de la imagen de referencia leidas como array

            #Aplicamos la mascara de las PIAs
            mask_curr_pia = np.ma.masked_where(mask1!=1,current)
            mask_ref_pia = np.ma.masked_where(mask1!=1,ref)
            mask_pias = np.ma.masked_where(mask1!=1,pias)
            cloud_pias = np.ma.masked_where(mask1!=1,cloud)
            #hemos aplicado la mascara y ahora guardamos una nueva matriz con la mascara aplicamos
            ref_PIA = np.ma.compressed(mask_ref_pia)
            current_PIA = np.ma.compressed(mask_curr_pia)
            pias_PIA = np.ma.compressed(mask_pias)
            cloud_PIA = np.ma.compressed(cloud_pias)

            #Aplicamos la mascara de NoData
            NoData_current_mask = np.ma.masked_where(current_PIA==255,current_PIA)
            NoData_ref_mask = np.ma.masked_where(current_PIA==255,ref_PIA)
            NoData_pias_mask = np.ma.masked_where(current_PIA==255,pias_PIA)
            NoData_cloud_mask = np.ma.masked_where(current_PIA==255,cloud_PIA)
            ref_PIA_NoData = np.ma.compressed(NoData_ref_mask)
            current_PIA_NoData = np.ma.compressed(NoData_current_mask)
            pias_PIA_NoData = np.ma.compressed(NoData_pias_mask)
            cloud_PIA_NoData = np.ma.compressed(NoData_cloud_mask)
            
            #Aplicamos la mascara de Nubes. se toma 1 porque se han igualado las 2 mascaras (Fmask y BQA)
            cloud_current_mask = np.ma.masked_where((cloud_PIA_NoData==1),current_PIA_NoData)
            cloud_ref_mask = np.ma.masked_where((cloud_PIA_NoData==1),ref_PIA_NoData)
            cloud_pias_mask = np.ma.masked_where((cloud_PIA_NoData==1),pias_PIA_NoData)
            
            ref_PIA_Cloud_NoData = np.ma.compressed(cloud_ref_mask)
            current_PIA_Cloud_NoData = np.ma.compressed(cloud_current_mask)
            pias_PIA_Cloud_NoData = np.ma.compressed(cloud_pias_mask)
            

            #Realizamos la 1 regresion
            slope, intercept, r_value, p_value, std_err = linregress(current_PIA_Cloud_NoData,ref_PIA_Cloud_NoData)
            #print '1 regresion: slope: '+ str(slope), 'intercept:', intercept, 'r', r_value, 'N:', len(ref_PIA_NoData)

            #Ahora tenemos los parametros para obtener el residuo de la primera regresion y 
            #eliminar aquellos que son mayores de abs(11.113949)
            esperado = current_PIA_Cloud_NoData * slope + intercept
            residuo = ref_PIA_Cloud_NoData - esperado

            mask_current_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=int(std), current_PIA_Cloud_NoData)
            mask_ref_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=int(std),ref_PIA_Cloud_NoData)
            mask_pias_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=int(std),pias_PIA_Cloud_NoData)
            current_PIA_NoData_STD = np.ma.compressed(mask_current_PIA_NoData_STD)
            ref_PIA_NoData_STD = np.ma.compressed(mask_ref_PIA_NoData_STD)
            pias_PIA_NoData_STD = np.ma.compressed(mask_pias_PIA_NoData_STD)

            #Hemos enmascarado los resiudos, ahora calculamos la 2 regresion
            slope, intercept, r_value, p_value, std_err = linregress(current_PIA_NoData_STD,ref_PIA_NoData_STD)
            print '\n++++++++++++++++++++++++++++++++++'
            print 'slope: '+ str(slope), 'intercept:', intercept, 'r', r_value, 'N:', len(ref_PIA_NoData_STD)
            print '++++++++++++++++++++++++++++++++++\n'

            #Los parametros estan ok, pero hay que hacer las mascaras de cada area PIA para ver el count
            values = {}
            values_str = {1: 'Mar', 2: 'Embalses', 3: 'Pinar', 4: 'Urbano-1', 5: 'Urbano-2', 6: 'Aeropuertos', 7: 'Arena', 8: 'Pastizales', 9: 'Mineria'}
            for i in range(1,10):
                mask_pia_= np.ma.masked_where(pias_PIA_NoData_STD != i, pias_PIA_NoData_STD)
                PIA = np.ma.compressed(mask_pia_)
                a = PIA.tolist()
                values[i] = len(a)
            #pasamos las claves de cada zona a string
            for i in values.keys():
                values[values_str[i]] = values.pop(i)
            print values,  #imprime el count de pixeles xa cada zona
            print banda_num
            #Generamos el raster de salida despues de aplicarle la ecuacion de regresion. Esto seria el nor2
            #Por aqui hay que ver como se soluciona
            if r_value > 0.85 and min(values.values()) >= 10:
                self.parametrosnor[banda_num]= {'Parametros':{'slope': slope, 'intercept': intercept, 'r': r_value, 'N': len(ref_PIA_NoData_STD), 'iter': self.iter}, 'Tipo_Area': values}
                
                print 'parametros en nor1: ', self.parametrosnor
                print '\comenzando nor2\n'
                self.nor2l8(banda, slope, intercept)#llamamos a nor2, Tambien funciona con L7
                print '\nNormalizacion de ', banda_num, ' realizada.\n'
            else:
                pass
                                       
                    
    def nor2l8(self, banda, slope, intercept):
    
        '''-----\n
        Este metodo aplica la ecuacion de la recta de regresion a cada banda (siempre que los haya podido obtener), y posteriormente
        reescala los valores para seguir teniendo un byte (0-255)'''
        
        path_geo = os.path.join(self.geo, self.escena)
        path_nor_escena = os.path.join(self.nor, self.escena)
        if not os.path.exists(path_nor_escena):
            os.makedirs(path_nor_escena)
        banda_num = banda[-6:-4]
        outFile = os.path.join(path_nor_escena, self.escena + '_grn1_' + banda_num + '.img')
        
        #metemos la referencia para el NoData, vamos a coger la banda 5 en geo (... Y por que no?)
        for i in os.listdir(path_geo):
            if i.endswith('b5.img'):
                
                ref = os.path.join(path_geo, i)
        
        with rasterio.open(ref) as src:
            ref_rs = src.read()
        
        with rasterio.open(banda) as src:

            rs = src.read()
            rs = rs*slope+intercept

            nd = (ref_rs == 0)
            min_msk =  (rs < 0)             
            max_msk = (rs>=255)

            rs[min_msk] = 0
            rs[max_msk] = 254

            rs = np.around(rs)
            rs[nd] = 255

            profile = src.meta
            profile.update(dtype=rasterio.uint8)

            with rasterio.open(outFile, 'w', **profile) as dst:
                dst.write(rs.astype(rasterio.uint8))
        #No data en 254!!
                    
    def copyDocR(self):
        
        '''-----\n
        Este metodo copia los doc y el rel generados por Miramon al hacer el Corrad y los pasa a nor'''

        path_rad = os.path.join(self.rad, self.escena)
        path_nor = os.path.join(self.nor, self.escena)
        
        for i in os.listdir(path_rad):
            
            if i.endswith('.doc') or i.endswith('.rel'):

                src = os.path.join(path_rad, i)
                dst = os.path.join(path_nor, i)
                shutil.copy(src, dst)
                            
        for i in os.listdir(path_nor):
            
            if i.endswith('.doc') or i.endswith('.rel'):
                src = os.path.join(path_nor, i)
                dst = os.path.join(path_nor, i.replace('_gr_', '_grn1_'))
                os.rename(src, dst)
                            
        print 'Archivos doc y rel copiados a nor'
        
        for i in os.listdir(path_nor):
            
            if i.endswith('b2.doc'):
                src = os.path.join(path_nor, i)
                dst = os.path.join(path_nor, self.escena + '_Fmask.doc')
                shutil.copy(src, dst)
                
        for i in os.listdir(path_nor):
            
            if i.endswith('Fmask.doc'):
                categorias = 'category  0 : Unclassified\ncategory  1 : Water\ncategory  2 : Shadow\ncategory  3 : Snow\ncategory  4 : Cloud\n'
                archivo = os.path.join(path_nor, i)
                doc = open(archivo, 'r')
                doc.seek(0)
                lineas = doc.readlines()
                for n,e in enumerate(lineas):
                    if e.startswith('max. value'):
                        lineas[n] = 'max. value  : 4\n'
                    elif e.startswith('legend cats'):
                        pos = n + 1
                        lineas[n] = 'legend cats : 5\n'
                    elif e.startswith('value units'):
                        lineas[n] = 'value units : Category\n'
                lineas.insert(pos, categorias)
                
                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)
        #Cerramos y a otra cosa mariposa
                f.close()
                
                        
    def modifyRelNor(self):
        
        '''-----\n
        Este metodo modifica el rel de nor para que tenga los valores correctos'''
        
        process = '[QUALITY:LINEAGE:PROCESS4]\nnOrganismes=1\nhistory=Creada con Auto Protocol (Python). Normalizacion banda a banda mediante regresion lineal. Parametros de calibracion (offset y gain) en el fichero coeficientes.txt de la escena en nor Paraetros calculados mediante regresion por minimos cuadrados partiendo de 60561 pixeles pseudoinvariantes definidos en 80 poligonos de 9 tipos (desde mar hasta arenas, ver tambien coeficientes.xt). Se eliminan nubes, valores perdidos y pixeles que cambian mas del 11,22, o 33 stds. Ver procedimiento detallado en la clase Protocolo (self.normalizacion). Imagen de referencia 20020718l7etm202_34_gr.\npurpose=Normalizacion radiometrica de la serie temporal\ndate=' + str(time.strftime("%Y%m%d %H%M%S00")) + '\n'
        tech = '\n[QUALITY:LINEAGE:PROCESS4:ORGANISME_1]\nIndividualName=Auto Protocol Proudly made by Diego Garcia Diaz\nPositionName=Tecnico LAST\nOrganisationName=(CSIC) LAST-EBD (APP)\n'
        pro = process + tech + '\n'
        
        #Buscamos el rel, lo abrimos en modo lectura y buscamos la linea donde queremos insertar el texto
        path_nor = os.path.join(self.nor, self.escena)
        
        for i in os.listdir(path_nor):
            if i.endswith('.rel'):
                rel_file = os.path.join(path_nor, i)
        
        if self.sat == 'L8':
            
            for line in fileinput.input(rel_file, inplace = 1): 
                print line.replace("_gr_", "_grn1_"),  
            for line in fileinput.input(rel_file, inplace = 1): 
                print line.replace("processes=1,2,3", "processes=1,2,3,4"),
            for line in fileinput.input(rel_file, inplace = 1): 
                print line.replace("IndexsNomsCamps=1-CA,2-B,3-G,4-R,5-NIR,6-SWIR1,7-SWIR2,9-CI", "IndexsNomsCamps=2-B,3-G,4-R,5-NIR,6-SWIR1,7-SWIR2"),

            rel_nor = open(rel_file, 'r')
            lineas = rel_nor.readlines()
            for i in range(len(lineas)):
                if lineas[i] == '[QUALITY:LINEAGE]\n':
                    pos = i

            #insertamos el texto
            lineas.insert(pos, pro)

            #Ahora cambiamos el nombre a las bandas e incluimos el proceso 4 en el quality linage process


            #Cerramos el rel
            rel_nor.close()

            for i in range(len(lineas)):
                if lineas[i] == '[ATTRIBUTE_DATA:1-CA]\n':
                    start_b1 = i
                elif lineas[i] == '[ATTRIBUTE_DATA:2-B]\n':
                    start_b2 = i
                elif lineas[i] == '[ATTRIBUTE_DATA:9-CI]\n':
                    start_b9 = i
                elif lineas[i].startswith('descriptor=Banda 7'):
                    lineas.insert(i+1, 'unitats=Refs*374\n')
                elif lineas[i].startswith('descriptor=Banda 6'):
                    lineas.insert(i+1, 'unitats=Refs*324\n')
                elif lineas[i].startswith('descriptor=Banda 5'):
                    lineas.insert(i+1, 'unitats=Refs*422\n')
                elif lineas[i].startswith('descriptor=Banda 4'):
                    lineas.insert(i+1, 'unitats=Refs*306\n')
                elif lineas[i].startswith('descriptor=Banda 3'):
                    lineas.insert(i+1, 'unitats=Refs*401\n')
                elif lineas[i].startswith('unitats=Refs(%)*254'):
                    lineas[i] = 'unitats=Refs*398\n'

            new_lineas = lineas[:start_b1] + lineas[start_b2:start_b9]


            for i in range(len(new_lineas)-2):
                if new_lineas[i].startswith('NomCamp_1') or new_lineas[i].startswith('NomCamp_9'):
                            new_lineas.remove(new_lineas[i])

            #Abrimos el rel en modo escritura y le pasamos las lineas con el proceso 4 ya insertado como argumento
            f = open(rel_file, 'w')
            for linea in new_lineas:
                f.write(linea)
            #Cerramos y a otra cosa mariposa
            f.close()
        
        else:
            
            for line in fileinput.input(rel_file, inplace = 1): 
                print line.replace("_gr_", "_grn1_"),  
            for line in fileinput.input(rel_file, inplace = 1): 
                print line.replace("processes=1,2,3", "processes=1,2,3,4"),
            
            rel_nor = open(rel_file, 'r')
            lineas = rel_nor.readlines()
            for i in range(len(lineas)):
                if lineas[i] == '[QUALITY:LINEAGE]\n':
                    pos = i

            #insertamos el texto
            lineas.insert(pos, pro)

            #Ahora cambiamos el nombre a las bandas e incluimos el proceso 4 en el quality linage process


            #Cerramos el rel
            rel_nor.close()

            for i in range(len(lineas)):
            
                if lineas[i].startswith('descriptor=Banda 7'):
                    lineas.insert(i+1, 'unitats=Refs*374\n')
                elif lineas[i].startswith('descriptor=Banda 6'):
                    lineas.insert(i+1, 'unitats=Refs*324\n')
                elif lineas[i].startswith('descriptor=Banda 5'):
                    lineas.insert(i+1, 'unitats=Refs*422\n')
                elif lineas[i].startswith('descriptor=Banda 4'):
                    lineas.insert(i+1, 'unitats=Refs*306\n')
                elif lineas[i].startswith('descriptor=Banda 3'):
                    lineas.insert(i+1, 'unitats=Refs*401\n')
                elif lineas[i].startswith('unitats=Refs(%)*254'):
                    lineas[i] = 'unitats=Refs*398\n'

            new_lineas = lineas

            #Abrimos el rel en modo escritura y le pasamos las lineas con el proceso 4 ya insertado como argumento
            f = open(rel_file, 'w')
            for linea in new_lineas:
                f.write(linea)
            #Cerramos y a otra cosa mariposa
            f.close()
            
        
    def fmask_binary(self):
    
        '''-----\n
        Este metodo sirve para reclasificar la salida de Fmask a una mascara binaria de 0 y 1'''
    
        path_nor = os.path.join(self.nor, self.escena)
        outFile = os.path.join(path_nor, self.escena + '_CM.img')

        for i in os.listdir(path_nor):
            if i.endswith('Fmask.img'):
                cloud = os.path.join(path_nor, i)

        with rasterio.drivers():
            with rasterio.open(cloud) as src:
                rs = src.read()
                clouds =  (rs == 2) | (rs == 4) #Aqui elegimos los pixeles con valor 2 (sombra de nubes) o 4 (nubes)
                sind = (rs!=2) & (rs!=4) #Todos los demas pixeles/valores

                rs[clouds] = 1
                rs[sind] = 0

                profile = src.meta
                profile.update(dtype=rasterio.uint8)

                with rasterio.open(outFile, 'w', **profile) as dst:
                    dst.write(rs.astype(rasterio.uint8))
                    
    def modify_hdr_rad_pro(self, ruta): 
    
    
        '''-----\n
        Este metodo corrige el ^P"@#&% tema de la proyeccion a ED50 PS, 
        que Dios quiera que pronto se cambie a ETRS89 (y ya puestos en huso 29)'''
        
        match = "map info = {UTM, 1.000, 1.000, 78000.000, 4269000.000, 3.0000000000e+001, 3.0000000000e+001, 30, North, European 1950 PS, units=Meters}\n"
        wave = "wavelength units = Unknown\n"
        css = 'coordinate system string = {PROJCS["UTM_Zone_30_Northern_Hemisphere",GEOGCS["GCS_European_1950",DATUM\
        ["D_European_1950",SPHEROID["International_1924",6378388,297]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]\
        ,PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-3]\
        ,PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["Meter",1]]}'
        #path_escena_geo = os.path.join(self.geo, self.escena)
        for i in os.listdir(ruta):

            if i.endswith('.hdr'):

                archivo = os.path.join(ruta, i)
                hdr = open(archivo, 'r')
                hdr.seek(0)
                lineas = hdr.readlines()
                for n,e in enumerate(lineas):
                    if e.startswith('map info'):
                        lineas[n] = match
                    #elif e.startswith('coordinate system string'):
                        #lineas[n] = css
                lineas.append(wave)

                hdr.close()

                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                print 'modificados (coordenadas) los metadatos de ', i
                
    def clean_nor(self):
    
        '''Este elimina del rel las bandas que no se han podido normalizar, junto con los docs sobrantes'''

        path_nor = os.path.join(self.nor, self.escena)
        for i in os.listdir(path_nor):
            if i.endswith('.rel'):
                rel = os.path.join(path_nor, i)

        #creamos 2 diccionarios para escribir el bat 
        if self.sat == 'L8':

            dcnor = {'b2': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:2-B\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:2-B:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_2-B\n',\
                    'b3': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:3-G\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:3-G:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_3-G\n',\
                    'b4': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:4-R\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:4-R:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_4-R\n',\
                    'b5': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:5-NIR\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:5-NIR:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_5-NIR\n',\
                    'b6': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:6-SWIR1\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:6-SWIR1:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_6-SWIR1\n',\
                    'b7': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:7-SWIR2\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:7-SWIR2:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_7-SWIR2\n'}
            
            dindex = {'b2': '2-B', 'b3': '3-G', 'b4': '4-R', 'b5': '5-NIR', 'b6': '6-SWIR1', 'b7': '7-SWIR2'}
        
        else:

            dcnor = {'b1': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:1-B\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:1-B:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_1-B\n',\
                     'b2': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:2-G\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:2-G:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_2-G\n',\
                     'b3': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:3-R\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:3-R:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_3-R\n',\
                     'b4': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:4-IRp\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:4-IRp:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_4-IRp\n',\
                     'b5': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:5-IRm1\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:5-IRm1:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_5-IRm1\n',\
                     'b7': 'C:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:7-IRm2\nC:\MiraMon\CanviREL 3' + ' ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA:7-IRm2:BAND\nC:\MiraMon\CanviREL 2' + ' ' + os.path.join(path_nor, rel) + ' ' + 'ATTRIBUTE_DATA NomCamp_7-IRm2\n'}
        
            dindex = {'b1': '1-B', 'b2': '2-G', 'b3': '3-R', 'b4': '4-IRp', 'b5': '5-IRm1', 'b7': '7-IRm2'}

        
        #creamos 4 listas: Una para las bandas img, otra para los docs, otra para los hdrs y una vacia donde iran las bandas a borrar
        bandas = [i[-6:-4] for i in os.listdir(path_nor) if i.endswith('.img') and 'grn1' in i]
        docs = [i for i in os.listdir(path_nor) if i.endswith('.doc') and 'grn1' in i]
        hdrs = [i for i in os.listdir(path_nor) if i.endswith('.hdr') and 'grn1' in i]
        todelete = []
        
        #agregamos las bandas a borrar a la lista todelete
        for i in dcnor.keys():
            if not i in bandas:
                todelete.append(i)
        print 'To Delete: ', todelete
            
        #comprobamos que no se hayan normalizado todas las bandas
        if len(todelete) > 0:
            
            #creamos el string necesario para la clave del rel IndexsNomsCamps
            a = [dindex[i] for i in bandas]
            s = (',').join(a)
            index = 'C:\MiraMon\CanviREL 1 ' + os.path.join(path_nor, rel) + ' ATTRIBUTE_DATA IndexsNomsCamps ' + s
            print 'Index: ', index

            #creamos un archivo bat en el que escribimos lo necesario para borrar las bandas que no se han podido normalizar del rel
            bat = os.path.join(self.data, 'canvirel.bat')
            l = open(bat, 'w')
            for i in todelete:
                l.write(dcnor[i])
            l.write(index)
            l.close()

            #ejecutamos el bat y lo borramos
            os.system(bat)
            os.remove(bat)

            #Ahora vamos a borrar los docs y hdrs de las bandas no normalizadas
            for banda in todelete:
                for i in os.listdir(path_nor):
                    if banda in i:
                        rs = os.path.join(path_nor, i)
                        os.remove(rs)
                        print 'borrado:', rs                        
        else:
            
            print 'Todas las bandas de la escena se han normalizado'
        
        if self.sat == 'L8':
            print 'Borrando bandas 1 y 9'
            for i in os.listdir(path_nor):
                if i.endswith('b1.doc') | i.endswith('b9.doc'):
                    print i
                    rs = os.path.join(path_nor, i)
                    os.remove(rs)
                    
    def caller(self):
    
        ar = os.path.join(self.data, 'caller.bat')
        arc = open(ar, 'r')
        cadena = 'call h:\\SIWeb\\imgs\\BATS\\prepara_una_imagen_LANDSAT_para_servidor.bat'
        lineas = arc.readlines()

        year = self.escena[:4]
        month = self.escena[4:6]
        day = self.escena[6:8]
        sat = self.escena[8:13]

        new = cadena + ' ' + year + ' ' + month + ' ' + day + ' ' + sat + '\n'
        lineas.append(new)

        caller = open(ar, 'w')
        caller.writelines(lineas)
        caller.close()
    
    
    def clouds(self):
        
        self.fmask()
        if self.sat == 'L7':
            if self.escena > '20030714':
                self.fmask_legend(self.gapfill)
            else:
                self.fmask_legend(self.ruta_escena)
        else:
            self.fmask_legend(self.ruta_escena)
        #self.mascara_cloud_pn()
        self.get_cloud_pn()
        
        
    def m_import(self):
        
        self.createI_bat()
        self.callI_bat()
                              
    def importacion(self):
        
        ini = time.time()
        
        self.clouds()
        self.m_import()
        self.get_kl_csw()
        self.remove_masks()
        
        print "Mascara de nubes, importacion y obtencion de kls concluido en  " + str(time.time() - ini) + " segundos"
        
    def reproyeccion(self):
        
        ini = time.time()
        
        self.reproject()
        self.copyDocG()
        self.modifyDocG()
        self.modifyRelG()
        path_geo = os.path.join(self.geo, self.escena)
        self.modify_hdr_rad_pro(path_geo)
        
        #Insertamos los datos en la MongoDB
        connection = pymongo.MongoClient("mongodb://localhost")
        db=connection.teledeteccion
        landsat = db.landsat
        
        try:
        
            landsat.update_one({'_id':self.escena}, {'$set':{'Info.Pasos.geo':{'Georef':'True', 'Fecha': datetime.now()}}})
            
        except Exception as e:
            print "Unexpected error:", type(e), e
            
        print "Reproyeccion realizada en  " + str(time.time() - ini) + " segundos"
        
    def Corrad(self):
        
        ini = time.time()
        
        self.copy_files_GR()
        self.createR_bat()
        self.callR_bat()
        self.cleanR()
        self.modify_hdr_rad()
        self.correct_sup_inf()
        self.clean_correct_R()
        self.modify_hdr_rad_255()
        self.translate_bytes_gdal() 
        self.modifyRelRad()
        self.re_clean_R()
        self.modifyDocR()
        self.path_geo = os.path.join(self.geo, self.escena)
        path_rad = os.path.join(self.rad, self.escena)
        self.modify_hdr_rad_pro(path_rad)
        
        #Sacamos los valores del kl. 
        
        for i in os.listdir(path_rad):
            
            if i.endswith('.rad') :
                rad = os.path.join(path_rad, i)
                f = open(rad, 'r')
                lista = []
                for l in f:
                    if re.search('Kl=', l) and not l.startswith(';'):
                        kl = int(l.split('=')[1].rstrip())
                        lista.append(kl)       
                f.close()
                
        bandas = ['b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b9']
        bandasl7 = ['b1', 'b2', 'b3', 'b4', 'b5', 'b7']
        
        if self.sat == 'L8':
            kl_values = dict(zip(bandas, lista))
        else:
            kl_values = dict(zip(bandasl7, lista))
                
        #Insertamos los datos en MongoDB
        connection = pymongo.MongoClient("mongodb://localhost")
        db=connection.teledeteccion
        landsat = db.landsat
        
        try:
        
            landsat.update_one({'_id':self.escena}, {'$set':{'Info.Pasos.rad': {'Corrad': 'True', 'Kl-Values': kl_values, 'Fecha': datetime.now()}}})
            
        except Exception as e:
            print "Unexpected error:", type(e), e
            
        print "Correccion radiometrica realizada en  " + str(time.time() - ini) + " segundos"
        
    
    def normalizacion(self):
        
        ini = time.time()
        
        self.normalize()
        self.copyDocR()
        self.modifyRelNor()
        path_escena_nor = os.path.join(self.nor, self.escena)
        self.fmask_legend(path_escena_nor)
        self.fmask_binary()
        path_nor = os.path.join(self.nor, self.escena)
        self.modify_hdr_rad_pro(path_nor)
        self.clean_nor()
        
        #Insertamos los datos en MongoDB
        connection = pymongo.MongoClient("mongodb://localhost")
        db=connection.teledeteccion
        landsat = db.landsat
        
        try:
        
            landsat.update_one({'_id':self.escena}, {'$set':{'Info.Finalizada': datetime.now()}})
            
        except Exception as e:
            print "Unexpected error:", type(e), e
                    
        print "Normalizacion realizada en  " + str(time.time() - ini) + " segundos"
        #No hemos insertado los datos en MongoDB en este caso porque se ha hecho directamente desde normalize
        
        
    def run_all(self): 
        
        #Lo mas comodo, desde aqui se llaman a todos los pasos. Se llama este metodo y en un cafe esta acabado
                
        ini = time.time()
        
        self.importacion()
        self.reproyeccion()
        self.Corrad()
        self.normalizacion()                       
        self.caller()      
        
        print "Escena finalizada en  " + str((time.time() - ini)/60) + " minutos"

### ToDo: Incluir download,  upload to venus 