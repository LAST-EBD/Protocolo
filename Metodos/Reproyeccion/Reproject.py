def reproject(ruta):
    
    
    import os, time
    from osgeo import gdal, gdalconst

    # Source
    ti = time.time()
    for i in os.listdir(ruta):
        
        if i.endswith('.TIF'):
            
            tini = time.time()
            print "Reproyectando ", i
            
            src_filename =  os.path.join(ruta, i)
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

            # Output / destination
            dst_filename = os.path.join(ruta,  i[:-4] + '.img')
            dst = gdal.GetDriverByName('ENVI').Create(dst_filename, wide, high, 1, gdalconst.GDT_UInt16)
            dst.SetGeoTransform( match_geotrans )
            dst.SetProjection( match_proj)

            # Do the work
            gdal.ReprojectImage(src, dst, src_proj, match_proj, gdalconst.GRA_Cubic)

            del dst # Flush
            
            print i + " reproyectada en " + str(time.time()-tini) + " segundos"
            
    print "Reproyección completa realizada en " + str((time.time()-ti)/60) + " minutos"