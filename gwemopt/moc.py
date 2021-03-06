import time

from mocpy import MOC
from astropy.table import Table
from joblib import Parallel, delayed
import healpy as hp
import numpy as np

import gwemopt.utils

def create_moc(params):

    nside = params["nside"]

    moc_structs = {}
    for telescope in params["telescopes"]:
        config_struct = params["config"][telescope]
        tesselation = config_struct["tesselation"]
        moc_struct = {}

        if params["doParallel"]:
            moclists = Parallel(n_jobs=params["Ncores"])(delayed(Fov2Moc)(params, config_struct, telescope, tess[1], tess[2], nside) for tess in tesselation)
            for ii, tess in enumerate(tesselation):
                index, ra, dec = tess[0], tess[1], tess[2]
                moc_struct[index] = moclists[ii]    
        else:
            for ii, tess in enumerate(tesselation):
                index, ra, dec = tess[0], tess[1], tess[2]
                index = index.astype(int)
                moc_struct[index] = Fov2Moc(params, config_struct, telescope, ra, dec, nside)
        moc_structs[telescope] = moc_struct

    return moc_structs

def Fov2Moc(params, config_struct, telescope, ra_pointing, dec_pointing, nside):
    """Return a MOC in fits file of a fov footprint.
       The MOC fov is displayed in real time in an Aladin plan.

       Input:
           ra--> right ascention of fov center [deg]
           dec --> declination of fov center [deg]
           fov_width --> fov width [deg]
           fov_height --> fov height [deg]
           nside --> healpix resolution; by default 
           """

    moc_struct = {}
    
    if config_struct["FOV_type"] == "square": 
        ipix, radecs, patch, area = gwemopt.utils.getSquarePixels(ra_pointing, dec_pointing, config_struct["FOV"], nside)
    elif config_struct["FOV_type"] == "circle":
        ipix, radecs, patch, area = gwemopt.utils.getCirclePixels(ra_pointing, dec_pointing, config_struct["FOV"], nside)

    if params["doChipGaps"]:
        npix = hp.nside2npix(nside)
        pixel_index = np.arange(npix)
        RAs, Decs = hp.pix2ang(nside, pixel_index, lonlat=True, nest=False)

        if telescope == "ZTF":
            Z = gwemopt.quadrants.ZTFtile(ra_pointing, dec_pointing, config_struct)
            #ipix = np.where(Z.inside_nogaps(RAs, Decs))[0]  # Ignore chip gaps
            ipix = np.where(Z.inside(RAs, Decs))[0]
        else:
            print("Requested chip gaps with non-ZTF detector, failing.")
            exit(0)

    moc_struct["ra"] = ra_pointing
    moc_struct["dec"] = dec_pointing
    moc_struct["ipix"] = ipix
    moc_struct["corners"] = radecs
    moc_struct["patch"] = patch
    moc_struct["area"] = area

    if False:
    #if len(ipix) > 0:
        # from index to polar coordinates
        theta, phi = hp.pix2ang(nside, ipix)

        # converting these to right ascension and declination in degrees
        ra = np.rad2deg(phi)
        dec = np.rad2deg(0.5 * np.pi - theta)

        box_ipix = Table([ra, dec], names = ('RA[deg]', 'DEC[deg]'),
                 meta = {'ipix': 'ipix table'})

        moc_order = int(np.log(nside)/ np.log(2))
        moc = MOC.from_table( box_ipix, 'RA[deg]', 'DEC[deg]', moc_order )

        moc_struct["moc"] = moc
    else:
        moc_struct["moc"] = []

    return moc_struct

