# Protocolo Automático Landsat 7 y 8 del LAST-EBD

Esta clase está hecha para ser usada como alternativa automatizada al protocolo para tratamiento de imágenes Landsat del
Laboratorio de SIG y Teledetección de la Estación Biológica de Doñana. La normalización consta de 4 métodos: Importación, Reproyección, Corrección Radiométrica y Normalización. 

    El único software necesario es Miramón, que se utiliza por su gestión de Metadatos. Se emplea en la Importación y en la Corrección Radiométrica
    y se llama mediante archivos bat. Para el resto de procesos se usan GDAL, Rasterio y otras librerías de Python. En general se tratan los rasters
    como arrays, lo que produce un rendimiento en cuanto a la velocidad de procesado bastante elevado. Para la normalización se emplea también una 
    mascara de nubes, que se obtiene empleando Fmask o la banda de calidad de Landsat 8 si fallara Fmask.

    El script requiere una estructura de carpetas en un mismo nivel (/ori, /geo, /rad, /nor y /data). En /data deben de estar los archivos necesarios para llevar a cabo la normalización:

        1) Escena de referencia Landsat 7 /20020718l7etm202_34, en formato img + doc + rel + hdr 
        2) Shape con los límites del Parque Nacional de Doñana para calcular la cobertura de nubes sobre Doñana
        3) Modelo Digital del Terreno lo bastante amplio como para englobar cualquier escena
        4) Mascaras equilibradas y no equilibradas y de tipos de áreas pseudo invariantes

    Además de estos requisitos, en la carpeta /rad debe de haber 2 archivos kl_l8.rad y kl_l7.rad donde se guardarán temporalmente los valores
    del objeto oscuro (proceso empleado para la Corrección Radiométrica) y el dtm de la escena. Si la escena es una Landsat 7 debe de tener una carpeta
    /gapfill donde se encuentren las bandas originales con el bandeado del gapfill corregido y la carpeta gapmask con las máscaras de esos gaps, ya 
    que se emplearan para una correcta búsqueda del objeto oscuro.

    Al finalizar el proceso tendremos en ori, geo, rad y nor las bandas en formato img + doc + rel + hdr pasadas ya de niveles digitales
    a reflectancia en superficie normalizada y toda la información del proceso almacenada en una base de datos MongoDB


Referencias: 

1) http://age-tig.es/2012_Madrid/ponencia1/Diaz-Delgado_final_par.pdf

2) http://digital.csic.es/bitstream/10261/47158/1/ten94.pdf

***Se recomienda abrir con Mozilla o Edge para ver el Manual en pdf renderizado directamente en GitHub***







