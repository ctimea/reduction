"""
Continuum imaging scripts.  There must be a ``continuum_mses.txt`` file in the
directory this is run in.  That file is produced by ``split_windows.py``.

You can set the following environmental variables for this script:
    EXCLUDE_7M=<boolean>
        If this parameter is set (to anything), the 7m data will not be
        included in the images if they are present.
"""

import os
from metadata_tools import determine_imsize, determine_phasecenter
from tasks import tclean, exportfits, plotms
from taskinit import msmdtool
msmd = msmdtool()

imaging_root = "imaging_results"
if not os.path.exists(imaging_root):
    os.mkdir(imaging_root)

# load the list of continuum MSes from a file
# (this file has one continuum MS full path, e.g. /path/to/file.ms, per line)
with open('continuum_mses.txt', 'r') as fh:
    continuum_mses = [x.strip() for x in fh.readlines()]

for continuum_ms in continuum_mses:

    # strip off .cal.ms
    basename = os.path.split(continuum_ms[:-7])[1]

    field = basename.split("_")[0]

    if os.getenv('EXCLUDE_7M'):
        msmd.open(continuum_ms)
        antennae = ",".join([x for x in msmd.antennanames() if 'CM' not in x])
        msmd.close()
        suffix = '12M'
    else:
        antennae = ""
        suffix = '7M12M'

    coosys,racen,deccen = determine_phasecenter(ms=continuum_ms, field=field)
    phasecenter = "{0} {1}deg {2}deg".format(coosys, racen, deccen)
    pixscale = 0.05
    imsize = list(determine_imsize(ms=continuum_ms, field=field,
                                   phasecenter=(racen,deccen), spw=0,
                                   pixscale=pixscale))
    cellsize = ['{0}arcsec'.format(pixscale)] * 2

    contimagename = os.path.join(imaging_root, basename) + "_" + suffix

    if not os.path.exists(contimagename+".uvwave_vs_amp.png"):
        # make a diagnostic plot to show the UV distribution
        plotms(vis=continuum_ms,
               xaxis='uvwave',
               yaxis='amp',
               avgchannel='1000', # minimum possible # of channels
               plotfile=contimagename+".uvwave_vs_amp.png",
               showlegend=True,
               showgui=False,
               antenna=antennae,
              )


    for robust in (-2, 0, 2):
        imname = contimagename+"_robust{0}".format(robust)

        if not os.path.exists(imname+".image.tt0"):
            tclean(vis=continuum_ms,
                   field=field.encode(),
                   imagename=imname,
                   gridder='mosaic',
                   specmode='mfs',
                   phasecenter=phasecenter,
                   deconvolver='mtmfs',
                   scales=[0,3,9,27,81],
                   nterms=2,
                   outframe='LSRK',
                   veltype='radio',
                   niter=10000,
                   usemask='auto-multithresh',
                   interactive=False,
                   cell=cellsize,
                   imsize=imsize,
                   weighting='briggs',
                   robust=robust,
                   pbcor=True,
                   antenna=antennae,
                  )

            exportfits(imname+".image.tt0", imname+".image.tt0.fits")
            exportfits(imname+".image.tt0.pbcor", imname+".image.tt0.pbcor.fits")
        else:
            print("Skipping completed file {0}".format(imname))
