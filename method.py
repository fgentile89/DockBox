import os
import sys
import stat
import shutil
import subprocess

import tools.PDB as pdbt
import tools.mol2 as mol2t

class DockingMethod(object):

    def __init__(self, name, site, options):

        self.name = name
        self.site = site
        self.options = options
        self.program = self.__class__.__name__.lower()

    def run_docking(self, file_r, file_l, extract, cleanup):
        """Run docking and cleanup poses on one receptor (file_r) and one ligand (file_l)"""

        curdir = os.getcwd()
        # find name for docking directory
        dockdir = self.name
        if self.site[0]:
            dockdir += '.' + self.site[0]

        # create directory for docking (remove directory if exists)
        #shutil.rmtree(dockdir, ignore_errors=True)
        #os.mkdir(dockdir)
        os.chdir(dockdir)

        print "Starting docking with %s..."%self.program.capitalize()
        print "The following options will be used:"
        print self.options

        ## (A) run docking
        #script_name = "run_" + self.program + ".sh"
        #self.write_docking_script(script_name, file_r, file_l)
        #os.chmod(script_name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR)

        ## running this script will run the docking procedure
        #subprocess.check_call("./" + script_name + " &> " + self.program + ".log", shell=True, executable='/bin/bash')

        # (B) extract docking results
        # after extract_docking_results all the extracted poses are saved in .mol2 files
        self.extract_docking_results('rec.out.pdb', 'lig.out.pdb', 'score.out', file_r, extract)

        # (C) remove intermediate files if required
        if cleanup:
            self.cleanup()

        os.chdir(curdir)
        print "Docking with %s done."%self.program.capitalize()

    def run_rescoring(self, file_rl):
        """Run rescoring for multiple receptor-ligand files (file_rl)"""

        # if only one file, convert it to a list
        file_rl = list(file_rl)
        file_rl_abs = []
        for filename in file_rl:
            file_rl_abs.append(os.path.abspath(filename))

        curdir = os.getcwd()
        # find name for scoring directory
        scordir = self.name
        if self.site[0]:
            scordir += '.' + self.site[0]
        shutil.rmtree(scordir, ignore_errors=True)
        os.mkdir(scordir)

        # change directory
        os.chdir(scordir)

        # iterate over all the poses
        for filename in file_rl_abs:
            with open(filename, 'r') as frl:
                is_protein = True
                ff = open('rec.pdb', 'w')
                for line in frl:
                    if line.startswith(('ATOM', 'HETATM')) and line[17:20] == 'LIG' and is_protein:
                        ff.close()
                        ff = open('lig.pdb', 'w')
                        is_protein = False
                    if line.startswith(('ATOM', 'HETATM', 'TER')):
                        ff.write(line)
                ff.close()

                # (A) write script
                script_name = "run_scoring_" + self.program + ".sh"
                self.write_rescoring_script(script_name, 'rec.pdb', 'lig.pdb')
                os.chmod(script_name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR)
       
                # (B) run scoring method
                subprocess.check_call("./" + script_name + " &> " + self.program + ".log", shell=True)
       
                # (C) extract docking results
                self.extract_rescoring_results('score.out')

        os.chdir(curdir)

    def remove_out_of_range_poses(self, files_l, file_s):

        center = map(float, self.site[1].split(','))
        boxsize = map(float, self.site[2].split(','))

        out_of_range_idxs = []

        for jdx, file_l in enumerate(files_l):
            isout = False
            coords = mol2t.get_coordinates(file_l)
            for coord in coords:
                for idx, xyz in enumerate(coord):
                    # check if the pose is out of the box
                    if abs(float(xyz)-center[idx]) > boxsize[idx]*1./2:
                        isout = True
                        break
            if isout:
                os.remove(file_l)
                out_of_range_idxs.append(jdx)

        with open(file_s, 'r') as sf:
            with open('score.tmp.out', 'w') as sft:
                for idx, line in enumerate(sf):
                    if idx not in out_of_range_idxs:
                        sft.write(line)

        shutil.move('score.tmp.out', file_s)

    def write_rescoring_script(self, script_name, file_r, file_l):
        pass

    def extract_rescoring_results(self, filename):
        pass

    def write_docking_script(self, script_name, file_r, file_l):
        pass

    def extract_docking_results(self, file_r, file_l, file_s, input_file_r, extract):
        pass

    def cleanup(self):
        pass
