import os, shutil, gdal, time #probar a quitar gdal de aqui
from osgeo import gdal, gdalconst

class Protocolo(object):
    
     #importar arcpy si finalmente es necesario para realizar la normalizacion (regresión)
    
    '''Esta clase está hecha para ser usada como alternativa automatizada al protocolo para tratamiento de imágenes landsat del
    Laboratorio de SIG y Teledetección de la Estación Biológica de Doñana. Consta de 4 métodos: Descarga, Importación a Miramon, 
    Corrección Radiométrica y Normalización'''
    
    def __init__(self, ruta):
        
        
        '''Aqui instanciamos la clase con la escena que queramos, hay que introducir la ruta a la carpeta en ori
        y de esa ruta el constructor obtiene el resto de rutas que necesita para ejecutarse'''
        
        self.ruta_escena = ruta
        self.ori = os.path.split(ruta)[0]
        self.escena = os.path.split(ruta)[1]
        self.raiz = os.path.split(self.ori)[0]
        self.geo = os.path.join(self.raiz, 'geo')
        self.rad = os.path.join(self.raiz, 'rad')
        self.nor = os.path.join(self.raiz, 'nor')
        self.mimport = os.path.join(self.ruta_escena, 'miramon_import')
        if not os.path.exists(self.mimport):
            os.makedirs(self.mimport)
        #mir_imp_bat = "import.bat"
        self.bat = os.path.join(self.ruta_escena, 'import.bat')
        self.bat2 = os.path.join(self.rad, 'importRad.bat')
        
    def createG_bat(self):
        
        '''Este metodo crea un archivo bat con los parametros necesarios para realizar la importacion'''

        #estas son las variables que necesarias para crear el bat de Miramon
        tifimg = 'C:\\MiraMon\\TIFIMG'
        num1 = '9'
        num2 = '1'
        num3 = '0'
        salidapath = self.mimport #aquí va la ruta de salida de la escena
        dt = '/DT=c:\\MiraMon'

        for i in os.listdir(self.ruta_escena):
            if i.endswith('B1.TIF'):
                banda1 = os.path.join(self.ruta_escena, i)
            elif i.endswith('MTL.txt'):
                mtl = "/MD="+self.ruta_escena+"\\"+i
            else: continue

        lista = [tifimg, num1, banda1,  salidapath, num2, num3, mtl, dt]
        print lista

        batline = (" ").join(lista)

        pr = open(self.bat, 'w')
        pr.write(batline)
        pr.close()


    def callG_bat(self):
        
        '''Este metodo llama ejecuta el bat de la importacion. Tarda entre 7 y 21 segundos en importar la escena'''

        import os, time
        ti = time.time()
        a = os.system(self.bat)
        a
        if a == 0:
            print "Escena importada con éxito en " + str(time.time()-ti) + " segundos"
        else:
            print "No se pudo importar la escena"
        #borramos el archivo bat creado para la importación de la escena, una vez se ha importado ésta
        os.remove(self.bat)
        
        
    def mascara_kl(self):
        
        '''Este metodo genera las mascaras de las zonas donde se suelen dar los kl'''#Editarlo y añadirle la umbria de Sierras de Cadiz
    
        import os, subprocess

        lista = ['B1', 'B2', 'B3', 'B4','B5', 'B6', 'B6', 'B7', 'B9']
        shape = r'C:\Users\Diego\Desktop\Landsat_8\normalizacion l8_shapes\embalses\Emb_Clip_Ori.shp'
        crop = "-crop_to_cutline"
        path_escena = os.path.join(self.ori, self.escena)
        
        for i in os.listdir(path_escena):

            banda = i[-6:-4]

            if banda in lista:

                cmd = ["gdalwarp", "-dstnodata" , "0" , "-cutline", ]
                path_masks = os.path.join(path_escena, 'masks')
                if not os.path.exists(path_masks):
                    os.makedirs(path_masks)

                raster = os.path.join(path_escena, i)
                salida = os.path.join(path_masks, i[-6:-4]+'_mask.TIF')
                cmd.insert(4, shape)
                cmd.insert(5, crop)
                cmd.insert(6, raster)
                cmd.insert(7, salida)

                proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                stdout,stderr=proc.communicate()
                exit_code=proc.wait()

                if exit_code: 
                    raise RuntimeError(stderr)
                #else: print stdout 
                    
        
    def make_hist(self):
        
        import os, pandas, gdal
        import matplotlib.pyplot as plt
        
        path_escena = os.path.join(self.ori, self.escena)
        path_masks = os.path.join(path_escena, 'masks')
        path_rad = os.path.join(self.rad, self.escena)
        if not os.path.exists(path_rad):
            os.makedirs(path_rad)
        
        for i in os.listdir(path_masks):
                    
            if i.endswith('.TIF'):

                rs = os.path.join(path_masks, i)
                raster = gdal.Open(rs)
                banda = i[:2]

                # read raster as array
                bandraster = raster.GetRasterBand(1)
                data = bandraster.ReadAsArray()
                mask = (data != 0)
                myArray = data[mask]

                lista = sorted(myArray.tolist())
                nmask = (myArray<lista[200])
                myArray2 = myArray[nmask]

                df = pandas.DataFrame(myArray2)
                plt.figure(); df.hist(figsize=(10,8), bins = 100)#incluir titulo y rotulos de ejes
                name = os.path.join(path_rad, self.escena + '_gr_' + banda.lower() + '.png')
                plt.savefig(name)
                    
                    
    def get_kl(self):
        
        '''Este metodo obtiene los kl, los pasa al archivo kl de rad y genera los histogramas 
        de los 200 valores mas bajos, para una posible comprobacion posterior'''
        #Guay, pero mirar si no es mirar reemplazar el kl.rad cada escena que se procese por uno en blanco en lugar de [:-4]
        import os, gdal

        lista_kl = []
        path_masks = os.path.join(self.ori, os.path.join(self.escena, 'masks'))
        
        for i in os.listdir(path_masks):

            if i.endswith('.TIF'):

                raster = os.path.join(path_masks, i)
                raster = gdal.Open(raster)

                # read raster as array
                bandraster = raster.GetRasterBand(1)
                arr_band = bandraster.ReadAsArray()
                mask = (arr_band != 0)
                myArray = arr_band[mask]

                kl = myArray.min()
                lista_kl.append(kl)
        
        for i in os.listdir(self.rad):
            
                if i.endswith('.rad'):

                    archivo = os.path.join(self.rad, i)
                    dictio = {6: lista_kl[0], 7: lista_kl[1], 8: lista_kl[2], 9: lista_kl[3], 10: lista_kl[4], 11: lista_kl[5], 12: lista_kl[6], 14: lista_kl[7]}

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
                    
        print 'modificados los metadatos del rad'
        
    
    def reproject(self):
        
        '''Este metodo reproyecta los geotiff originales, tomando todos los parametros que necesita para la salida, 
        extent, SCR, etc. Al mismo tiempo los cambia a formato img + hdr'''
        
        dgeo = {'B1': '_g_b1.img', 'B2': '_g_b2.img', 'B3': '_g_b3.img', 'B4': '_g_b4.img', 'B5': '_g_b5.img',\
             'B6': '_g_b6.img', 'B7': '_g_b7.img', 'B8': '_g_b8.img', 'B9': '_g_b9.img',\
           'B10': '_g_b10.img', 'B11': '_g_b11.img', 'BQA': '_g_bqa.img'}
        
        #cremos la carpeta con la ruta de destino
        destino = os.path.join(self.geo, self.escena)
        os.mkdir(destino)
        # Source
        ti = time.time()
        for i in os.listdir(self.ruta_escena):

            if i.endswith('.TIF'):

                tini = time.time()
                print "Reproyectando " + i

                src_filename =  os.path.join(self.ruta_escena, i)
                src = gdal.Open(src_filename, gdalconst.GA_ReadOnly)
                src_proj = src.GetProjection()
                src_geotrans = src.GetGeoTransform()

                # We want a section of source that matches this:
                match_filename = r'C:\Users\Diego\Desktop\Protocolo\PruebasGdalReproject\20020718l7etm202_34\20020718l7etm202_34_grn1_b5.img'
                match_ds = gdal.Open(match_filename, gdalconst.GA_ReadOnly)
                match_proj = match_ds.GetProjection()
                match_geotrans = match_ds.GetGeoTransform()
                wide = match_ds.RasterXSize
                high = match_ds.RasterYSize

                #prueba con el dgeo
                banda = None
                if len(i) == 28:
                    banda = i[-6:-4]
                else:
                    banda = i[-7:-4]
                    
                dst_filename = os.path.join(destino, self.escena + dgeo[banda])
                
                # Output / destination
                
                dst = gdal.GetDriverByName('ENVI').Create(dst_filename, wide, high, 1, gdalconst.GDT_UInt16)
                dst.SetGeoTransform(match_geotrans)
                dst.SetProjection(match_proj)

                # Do the work
                gdal.ReprojectImage(src, dst, src_proj, match_proj, gdalconst.GRA_Cubic)

                del dst # Flush

                print i + " reproyectada en " + str(time.time()-tini) + " segundos"

        print "Reproyección completa realizada en " + str((time.time()-ti)/60) + " minutos"
        
    def copyDocG(self):
        
        '''Este metodo copia los doc y el rel generados por Miramon al importar la imagen y los pasa a geo'''

        rutageo = os.path.join(self.geo, self.escena)
        for i in os.listdir(self.mimport):
    
            d = {'B1-CA': '_g_b1', 'B10-LWIR1': '_g_b10', 'B11-LWIR2': '_g_b11', 'B2-B': '_g_b2', 'B3-G': '_g_b3', 'B4-R': '_g_b4', 'B5-NIR': '_g_b5', 'B6-SWIR1': '_g_b6', 'B7-SWIR2': '_g_b7',\
                'B8-PAN': '_g_b8', 'B9-CI': '_g_b9', 'BQA-CirrusConfidence': '_g_BQA-Cirrus', 'BQA-CloudConfidence': '_g_BQA-Cloud', 'BQA-DesignatedFill': '_g_BQA-DFill',\
                'BQA-SnowIceConfidence': '_g_BQA-SnowIce', 'BQA-TerrainOcclusion': '_g_BQA-Terrain', 'BQA-WaterConfidence': '_g_BQA-Water'}

            if i.endswith('.doc'):
                
                number = i[20:-7]
                key = d[number]
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
        
        '''Este metodo edita los doc copiados a geo para que tenga los valores correctos'''
        
        ruta = os.path.join(self.geo, self.escena)
        for i in os.listdir(ruta):
        #print i
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
                    #elif lineas[l].startswit('comment'):
                        #lineas[l].drop()
                    else: continue

                doc.close()

                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                print 'modificados los metadatos de ', i
                
    def modifyRelG(self):
        
        '''Este metodo modifica el rel de geo para que tenga los valores correctos'''
        
        ruta = os.path.join(self.geo, self.escena)
        for i in os.listdir(ruta):
            if i.endswith('rel'):
                rel_file = os.path.join(ruta, i)
        
        rel = open(rel_file, 'r')
        lineas = rel.readlines()
        
        dgeo = {'B1-CA': '_g_b1', 'B10-LWIR1': '_g_b10', 'B11-LWIR2': '_g_b11', 'B2-B': '_g_b2', 'B3-G': '_g_b3', 'B4-R': '_g_b4', 'B5-NIR': '_g_b5', 'B6-SWIR1': '_g_b6', 'B7-SWIR2': '_g_b7',\
                'B8-PAN': '_g_b8', 'B9-CI': '_g_b9', 'BQA-CirrusConfidence': '_g_BQA-Cirrus', 'BQA-CloudConfidence': '_g_BQA-Cloud', 'BQA-DesignatedFill': '_g_BQA-DFill',\
                'BQA-SnowIceConfidence': '_g_BQA-SnowIce', 'BQA-TerrainOcclusion': '_g_BQA-Terrain', 'BQA-WaterConfidence': '_g_BQA-Water'}
        
        for l in range(len(lineas)):
    
            if lineas[l].startswith('FileIdentifier'):
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
            
            
    def copy_files_GR(self):
        
        '''Este metodo copia las bandas de 1 a 9 de geo a rad, para proceder a la corrección radiométrica'''
        
        import os, shutil

        #dgeoRad = {'b2': '_g_b1', 'b3': '_g_b2', 'b4': '_g_b3', 'b5': '_g_b4', 'b6': '_g_b5', 'b7': '_g_b7'}
        lista_bandas = ['b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b9']

        path_escena_geo =  os.path.join(self.geo, self.escena)
        path_escena_rad =  os.path.join(self.rad, self.escena)
        if not os.path.exists(path_escena_rad):
            os.makedirs(path_escena_rad)
        #if not os.path.exists(path_escena):
         #   os.makedirs(path_escena)

        for i in os.listdir(path_escena_geo):

            #print i
            banda = i[-6:-4]

            if banda in lista_bandas:

                #key = dgeoRad[banda]
                #end = i[-4:]

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
        
        '''Este metodo crea el bat para realizar la correción radiométrica'''

        #estas son las variables que necesarias para crear el bat de Miramon
        #Esta ok, working fine!
        path_escena_rad = os.path.join(self.rad, self.escena)
        corrad = 'C:\MiraMon\CORRAD'
        num1 = '1'
        dtm = os.path.join(self.rad, 'sindato.img')
        kl = os.path.join(self.rad, 'kl.rad')
        string = '/MULTIBANDA /CONSERVAR_MDT /LIMIT_LAMBERT=73.000000 /DT=c:\MiraMon'

        for i in os.listdir(os.path.join(self.rad, self.escena)):#cambiar ruta escena x lo que corresponda
            if i.endswith('b1.img'):
                banda1 = os.path.join(path_escena_rad, i)
            else: continue

        lista = [corrad, num1, banda1, path_escena_rad,  dtm, kl, string]
        print lista

        batline = (" ").join(lista)

        pr = open(self.bat2, 'w')#crear un nuevo bat2
        pr.write(batline)
        pr.close()


    def callR_bat(self):

        '''Este ejecuta el bat que realiza la correción radiométrica'''
        
        import os, time
        ti = time.time()
        print 'Llamando a Miramon... Miramon!!!!!!'
        a = os.system(self.bat2)
        a
        if a == 0:
            print "Escena corregida con éxito en " + str(time.time()-ti) + " segundos"
        else:
            print "No se pudo realizar la corrección de la escena"
        #borramos el archivo bat creado para la importación de la escena, una vez se ha importado ésta
        os.remove(self.bat2)
        
        
    def cleanR(self):
        
        '''Este metodo borra los archivos copiados de geo, de modo que nos quedamos solo con los hdr y los img y doc generado 
        por el Corrad''' 
        
        path_escena_rad = os.path.join(self.rad, self.escena)
        for i in os.listdir(path_escena_rad):
            if not i.startswith('r_') and not i.endswith('.hdr'):#check this out
                os.remove(os.path.join(path_escena_rad, i))
            elif i.endswith('.hdr'):
                src = os.path.join(path_escena_rad, i)
                dst = os.path.join(path_escena_rad, i[:21]+'r'+i[-7:])
                os.rename(src, dst)
                
    def modify_hdr_rad(self):
        
        '''Este metodo edita los hdr para que tengan el valor correcto (FLOAT) para poder ser entendidos por GDAL.
        Hay que ver si hay que establecer primero el valor como No Data'''
        
        import os
                
        path_escena_rad = os.path.join(self.rad, self.escena)
        for i in os.listdir(path_escena_rad):
        #print i
            if i.endswith('.hdr'):

                archivo = os.path.join(path_escena_rad, i)
                hdr = open(archivo, 'r')
                hdr.seek(0)
                lineas = hdr.readlines()
                for l in range(len(lineas)):
                    if l == 8:
                        lineas[l] = 'data type = 4\n'
                 
                hdr.close()

                f = open(archivo, 'w')
                for linea in lineas:
                    f.write(linea)

                f.close()
                print 'modificados los metadatos de ', i
                
    def translate_bytes(self):
    
        import os, subprocess
        
        path_escena_rad = os.path.join(self.rad, self.escena)
        cmd = "gdal_translate -ot Byte -of ENVI -scale 0.00001 100.00000 1 255 -a_nodata 0 input output"

        for i in os.listdir(path_escena_rad):

            if i.endswith('img'):

                input_rs = os.path.join(path_escena_rad, i)
                newname = i[:-4]+'_byte'+i[-4:]
                output_rs = os.path.join(path_escena_rad, newname)
                #output_rs = os.path.join(ruta, i[:-4]+'_byte.img')
                #trans = 'gdal_translate'

                cmd = ["gdal_translate", "-ot",  "Byte" , "-of",  "ENVI" , "-scale",  "0.00001", "100.00000", "1", "255", "-a_nodata",  "0"]
                cmd.insert(12, input_rs)
                cmd.insert(13, output_rs)
                print cmd

                proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                stdout,stderr=proc.communicate()
                exit_code=proc.wait()

                if exit_code: 
                    raise RuntimeError(stderr)
                else: 
                    print stdout 
                
    def renameR(self):
        
        #Nooo
        path_escena_rad = os.path.join(self.rad, self.escena)
        for i in os.listdir(path_escena_rad):
            if not i.endswith('.hdr'):
                arc = os.path.join(path_escena_rad, i)
                newname = i[2:23]+'r'+i[-7:]
                newescena = os.path.join(path_escena_rad, newname)
                os.rename(arc, newescena)
            
    def modifyRelRad(self):
        
        
        '''Este metodo modifica el rel de geo para que tenga los valores correctos'''
        
        ruta = os.path.join(self.rad, self.escena)
        print ruta
        for i in os.listdir(ruta):
            if i.endswith('rel'):
                rel_file = os.path.join(ruta, i)
        print rel_file
        
        rel = open(rel_file, 'r')
        lineas = rel.readlines()
        
        drad = {'b1': '_gr_b1.img', 'b2': '_gr_b2.img', 'b3': '_gr_b3.img', 'b4': '_gr_b4.img', 'b5': '_gr_b5.img','b6': '_gr_b6.img', 'b7': '_gr_b7.img', 'b8': '_gr_b8.img', 'b9': '_gr_b9.img'}
        
        for l in range(len(lineas)):
            
            if lineas[l].startswith('NomFitxer=r_'):
                
                bandname = lineas[l][-7:-5]
                
                lineas[l] = lineas[l][:10] + self.escena + drad[bandname]+'\n'
                #print lineas[l]
            
            else: continue
                
        rel.close()

        #new_list = lineas[:start_band_name]+lineas[end_band_name:start_b8]+lineas[end_b8:start_end]
        #new_list.remove('NomCamp_8-PAN=8-PAN\n') Ver que hay que borrar e insertar (process 2 y 3)
        
        f = open(rel_file, 'w')
        for linea in lineas:
            f.write(linea)

        f.close()
        
    def importacion(self):
        
        self.createG_bat()
        self.callG_bat()
        
    def kl(self):
        import time
        ini = time.time()
        self.mascara_kl()
        self.make_hist()
        self.get_kl()
        print "obtenidos los kl y escrito el .rad en " + str(time.time() - ini) + " segundos"
        
    def reproyeccion(self):
        
        import time
        ini = time.time()
        
        self.reproject()
        self.copyDocG()
        self.modifyDocG()
        self.modifyRelG()
        
        print "Reproyeccion realizada en  " + str(time.time() - ini) + " segundos"
        
    def Corrad(self):
        #ahora está ok. 10/07/2015. Faltaría sacarle un rel a las imagenes en byte
        import time
        ini = time.time()
        self.copy_files_GR()
        self.createR_bat()
        self.callR_bat()
        self.cleanR()
        self.renameR()
        self.modify_hdr_rad()
        self.translate_bytes()
        self.modifyRelRad()
        
        print "Correccion radiometrica realizada en  " + str(time.time() - ini) + " segundos"
        
    def run_all(self):
        
        import time
        ini = time.time()
        
        self.importacion()
        self.reproyeccion()
        self.Corrad()
        
        print "Escena normalizada en  " + str((time.time() - ini)/60) + " minutos"

### Hasta aquí va todo ok, importo, reproyecto, corrad (son kl automatico aun) y cambio los .doc y rels
#queda cambiar el datatype de los hdr de rad de 12 a 4 para poder hacer el translate a bytes
#Y normalizar!!