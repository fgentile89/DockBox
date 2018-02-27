import os
import sys
import glob
import shutil
import subprocess
import autodock

from mdtools.utility import mol2

required_programs = ['prepare_ligand4.py', 'prepare_receptor4.py', 'vina', 'babel']

default_settings = {'cpu': '1', 'num_modes': '9', 'energy_range': '3'}

class Vina(autodock.ADBased):

    def __init__(self, instance, site, options):

        super(Vina, self).__init__(instance, site, options)

        center = map(str.strip, site[1].split(','))
        boxsize = map(str.strip, site[2].split(','))

        for idx, xyz in enumerate(['x', 'y', 'z']):
            self.options['center_'+xyz] = center[idx]
            self.options['size_'+xyz] = boxsize[idx]

    def write_docking_script(self, filename, file_r, file_l, file_q, rescoring=False):
        """write docking script for Vina"""

        locals().update(self.options)

        self.write_check_lig_pdbqt_script()
        self.write_check_nonstd_residues_script()

        # write vina config file
        with open('vina.config', 'w') as cf:
            # write mandatory options
            print >> cf, 'receptor = target.pdbqt'
            print >> cf, 'ligand = lig.pdbqt'
            # write other options
            for key, value in self.options.iteritems():
                print >> cf, key + ' = ' + value

        file_q_str = ''
        if file_q: file_q_str = str(file_q)
    
        # write vina script
        if not rescoring:
            with open(filename, 'w') as file:
                script ="""#!/bin/bash
set -e
# generate .pdbqt files
# ligand
prepare_ligand4.py -l %(file_l)s -o lig.pdbqt
python check_lig_pdbqt.py lig.pdbqt

# receptor
prepare_receptor4.py -U nphs_lps_waters -r %(file_r)s -o target.pdbqt &> prepare_receptor4.log
python check_nonstd_residues.py target.pdbqt %(file_q_str)s

# run vina
vina --config vina.config 1> vina.out 2> vina.err"""% locals()
                file.write(script)
        else:
            with open(filename, 'w') as file:
                script ="""#!/bin/bash
set -e
# generate .pdbqt files
prepare_ligand4.py -l %(file_l)s -o lig.pdbqt
python check_lig_pdbqt.py lig.pdbqt

if [ ! -f target.pdbqt ]; then
  prepare_receptor4.py -U nphs_lps_waters -r %(file_r)s -o target.pdbqt > prepare_receptor4.log
  python check_nonstd_residues.py target.pdbqt %(file_q_str)s
fi

# run vina
vina --score_only --config vina.config > vina.out"""% locals()
                file.write(script)

    def extract_docking_results(self, file_s, input_file_r, input_file_l):
        """Extract output structures in .mol2 formats"""

        if os.path.exists('lig_out.pdbqt'): 
            # extract structures from .pdbqt file 
            with open('lig_out.pdbqt','r') as pdbqtf:
                with open(file_s, 'w') as sf:
                    for line in pdbqtf:
                        if line.startswith('REMARK VINA RESULT:'):
                            score = float(line[19:].split()[0])
                            print >> sf, score

        subprocess.check_output('babel -ipdbqt lig_out.pdbqt -omol2 lig-.mol2 -m &>/dev/null',shell=True, executable='/bin/bash')
        self.update_output_mol2files(sample=input_file_l)

    def write_rescoring_script(self, filename, file_r, file_l, file_q):
        self.write_docking_script(filename, file_r, file_l, file_q, rescoring=True)
    
    def extract_rescoring_results(self, filename):

        with open(filename, 'a') as ff:
            with open('vina.out', 'r') as outf:
                for line in outf:
                    if line.startswith('Affinity:'):
                        print >> ff, line.split()[1]
        filenames = ['lig.pdbqt', 'target.pdbqt']
        for ff in filenames:
            if os.path.isfile(ff):
                os.remove(ff)
  
    def cleanup(self):
        pass
