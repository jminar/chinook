#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 29 16:36:23 2017

@author: ryanday
MIT License

Copyright (c) 2018 Ryan Patrick Day

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

'''
Generate a slab of lattice points and expand the lattice Hamiltonian to accommodate the modified basis
implicit in the slab generation

'''

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import ubc_tbarpes.orbital as olib
from operator import itemgetter

import ubc_tbarpes.TB_lib as TB_lib


def region(num):
    '''
    Generate a symmetric grid of points in number of lattice vectors. The tacit assumption is a 3 dimensional lattice
    args: num -- integer--grid will have size 2*num+1 in each direction
    returns numpy array of size ((2*num+1)**3,3) with centre value of first entry of (-num,-num,-num),...,(0,0,0),...,(num,num,num)
    '''
    num_symm = 2*num+1
    return np.array([[int(i/num_symm**2)-num,int(i/num_symm)%num_symm-num,i%num_symm-num] for i in range((num_symm)**3)])




class slab:
    
    def __init__(self,hkl,cells,buff,avec,basis,term):
        self.hkl = hkl
        self.cells = cells
        self.avec = avec
        self.buffer = buff
        if self.buffer%2 == 1:
            self.buffer+=1
        self.basis = basis
        self.term = term
        self.avslab,self.slab_base = self.gen()
     
    def vec_new(self,mesh,avn,l_oth,ind):
        '''
        With the slab normal vector defined, need now to redefine the in-plane vectors
        To do this, we look over the mesh of lattice points and find the nearest ones which
        are mutually orthogonal, and also to the normal vector as well.
        args:
            mesh -- mesh of lattice points (some number of len 3 numpy arrays of int The values are # of original lattice vectors from origin)
            avn -- the initialized new lattice vectors (only #3 is well defined as the normal vector) len 3 numpy array of float
            l_oth -- the length of the current minimal orthogonal vector satisfying the conditions (float)
            ind -- index of whether we are looking for the 1st or 2nd other lattice vector
        returns:
            avn -- the new lattice vectors (3 x 3 numpy array of float)
        '''
        for mvec in mesh:
            tmp = np.dot(mvec,self.avec)
            if ind==0:
                boolval = np.linalg.norm(np.dot(tmp,avn[-1,:]))<10.0**-5
            elif ind==1:
                boolval = (np.linalg.norm(np.dot(tmp,avn[-1,:]))<10.0**-5 and np.linalg.norm(np.dot(tmp,avn[0,:]))<10.0**-5)
            if boolval:
                if (np.linalg.norm(tmp)<l_oth or l_oth==0):
                    avn[ind,:] = tmp
                    l_oth = np.linalg.norm(tmp)
            
        return avn
    
    def plot_lattice(self,lpts):
        fig = plt.figure()
        ax = fig.add_subplot(111,projection='3d')
        ax.scatter(lpts[:,0],lpts[:,1],lpts[:,2])
        
    def gen(self):
        ''''
        Generate the new lattice. Establish the new lattice vectors.
        '''
        uv_norm = np.array([np.dot(self.hkl,avec)/np.linalg.norm(avec) for avec in self.avec]) #projection of normal in units of lattice vectors
        proj_norm = np.dot(uv_norm,self.avec) #normal projection vector in absolute units
        lpts = np.array([n*uv_norm for n in range(int(self.cells+self.buffer))]) #series of lattice vectors along normal direction subsumed by slab
        thick = np.linalg.norm(proj_norm*int(self.cells)) #thickness of slab in absolute units
        buff_thick = np.linalg.norm(int(self.buffer)*proj_norm) #thickness of buffer in absolute units
        print('Slab thickness: {:0.2f} A'.format(thick))
        print('Buffer layer thickness: {:0.2f} A'.format(buff_thick))
        
        #plot the lattice points along the normal
#        self.plot_lattice(lpts)
        
        mesh = region(10)
        # initialize the new lattice vectors
        av_new = np.zeros((3,3))
        
        # the normal vector should be one of the basis vectors
        av_new[-1,:] = proj_norm*(self.buffer+self.cells)
        # find the shortest lattice point in the mesh that is perpendicular to the slab normal
            
        av_new = self.vec_new(mesh,av_new,0.0,0)
        av_new = self.vec_new(mesh,av_new,np.linalg.norm(av_new[0,:]),1)

        
        #Need to populate the basis. 
        #generate a symmetric mesh of lattice points, populate with full basis, find 
        #which of the orbitals in the cluster are closest to the origin than other lattice points
        base_expand = []

        new_mesh = region(2) #smaller mesh near origin. NEED: more generic way to extend the lattice and get everything I want. i.e. 2 is not always enough!
        tmax = np.zeros(5)
        for m in new_mesh:
            origin = np.dot(m,av_new)
            for l in lpts:
                og_vec = origin+np.dot(l,self.avec)
                for b in self.basis: 
                    tmp = b.pos+og_vec
                    vproj = np.array([np.dot(tmp,avec)/np.linalg.norm(avec)**2 for avec in av_new])
                    # if the projection of the orbital position onto the new lattice vector is closer than any
                    #other of the new lattice points. This needs to be done carefully since some choices of basis
                    #will have elements inside neighbouring cells. Need to make sure we catch everyone!
                    if 0<=vproj[0]<1 and 0<=vproj[1]<1 and 0<vproj[2]<=thick/(thick+buff_thick):
                        tmp = b.copy()
                        tmp.pos = b.pos+ og_vec
                        tmp.slab_index = b.index
                        #find the highest instance of the termination atom
                        if tmp.atom == self.term:
                            pr_b = np.dot(tmp.pos,av_new[2])/np.linalg.norm(av_new[2])
                            if pr_b>=tmax[1]: 
                                tmax = np.array([tmp.index,pr_b,tmp.pos[0],tmp.pos[1],tmp.pos[2]])
                        base_expand.append(tmp)
#        print('tmax: ',tmax)
        #terminate the lattice, and redefine positions/labels accordingly              
        base_term = []
        for b in range(len(base_expand)):
            vec  = base_expand[b].pos - np.array(tmax[2:5])
            if -thick<=np.dot(vec,av_new[2])/np.linalg.norm(av_new[2])<=0.0:
                tmp_base = base_expand[b].copy()
                tmp_base.pos = vec
                base_term.append(tmp_base)
                base_term[-1].index = len(base_term)-1
                
        slab_base = self.nproj(av_new,base_term)
        
        return av_new,slab_base
    
    
    def nproj(self,an,blist):
        '''
        Organize the orbitals in slab-basis in terms of their projection onto the slab normal.
        This establishes a clear 'layer' order for the slab. This is essential to making a straightforward
        redefinition of the Hamiltonian for a slab geometry
        '''
        
        uv_norm = np.array([np.dot(self.hkl,avec)/np.linalg.norm(avec) for avec in self.avec]) #projection of normal in units of lattice vectors
        proj_norm = np.dot(uv_norm,self.avec) #normal projection vector in absolute units
        projections = np.zeros((len(blist),2))
        for b in list(enumerate(blist)):
            projections[b[0],0] = b[1].index
            projections[b[0],1] = int(np.dot(b[1].pos,proj_norm)/np.linalg.norm(proj_norm)**2)
        
        
        projections = np.array(sorted(projections,key=itemgetter(1)))
        for k in range(len(projections)):
            blist[int(projections[k,0])].index = k #this is a new attribute special to slabs
            
        b_organized = olib.sort_basis(blist,True)
        return b_organized
    
    
    
    ##After that I need to restructure the Hamiltonian to include all the new
    ##duplicates.
    ##
    
    def slab_TB(self,H,Hargs):
        '''
        Utility script for building a Slab Tight-Binding Model from a predetermined bulk TB for a periodic
        lattice
        
        
        args:
            H -- Hamiltonian object from bulk 
            og -- original basis size (int)
            sbase -- slab basis -- list of orbitals 
            Hargs -- dictionary 'cutoff','renorm','offset','tol','so': float,float,float,float,boolean
        
        return: TB object for the slab Hamiltonian
            
        The H_library produces a list of H objects which have attributes i,j,and then a list of [Re(H),Im(H),Vector]
        This has been defined for a bulk calculation. We need to:
            1. Rewrite the i,j pairs in H to reflect the new basis indexing (go through original basis, project along the normal direction and rewrite)
            2. Include also the Hermitian conjugates (R->-R, H->H*, swap i' and j')
            3. Expand the full H as a single list, sort by i,j
            4. Go through the new H list. If the projection of R onto normal is > 1 layer, then tack on the length of basis to j
            5. Now we have rewritten the connection between original Hamiltonian, and the new basis. The step which remains is to generate a copy
                for each instance of an identical atom in the lattice. That is  -- every 
                
        '''
        uv_norm = np.array([np.dot(self.hkl,avec)/np.linalg.norm(avec) for avec in self.avec]) #projection of normal in units of lattice vectors
        proj_norm = np.dot(uv_norm,self.avec) #normal projection vector in absolute units
        
        #add layer-information to the H-elements
        H_primitive = []
        for h in H:
            h_el = []
            for hi in h:
                layers = int(np.dot(np.array([hi[0],hi[1],hi[2]]),proj_norm)/np.linalg.norm(proj_norm)**2)
                h_el.apend([hi[0],hi[1],hi[2],hi[3],layers])
            H_primitive.append(TB_lib.H_me(h.i,h.j))
            H_primitive[-1].H = h_el
            #add the Hermitian conjugate too
            H_primitive.append(TB_lib.H_me(h.j,h.i))
            H_primitive[-1].H = HC(h_el)
        
        H_slab = []
        for orbital in self.slab_base:
            for h in H_primitive:
                if h.i==orbital.index:
                    for hi in h.H:
                        o2 = int(orbital.slab_index/len(self.basis))+h.j+len(self.basis)*hi[-1]
                        if h.i<=o2<len(self.slab_base):
                            H_slab.append([orbital.slab_index,o2,hi[0],hi[1],hi[2],hi[3]])
                            
        Hnew_args = {'type':'list','list':H_slab}.update(Hargs)
        
        slab_TB = TB_lib.TB_model(self.slab_base,Hnew_args)
            
        return slab_TB
    
    
def HC(hlist):
    return [[-h[0],-h[1],-h[2],np.conj(h[3]),-h[4]] for h in hlist]
        
        

if __name__=="__main__":

    avec = np.array([[1,0,0],[0,1,0],[0,0,3]])
    hkl = np.array([0,0,1])
    cells = 6
    buff = 5
    
    
    Z = [26,34]
    label = ['32xy','41z','32xy','41z']
    pos = [np.array([0.25,0.75,0.0]),np.array([0.25,0.25,0.13]),np.array([0.75,0.25,0.0]),np.array([0.75,0.75,0.87])]
    basis = [olib.orbital(0,0,label[0],pos[0],Z[0]),olib.orbital(1,1,label[1],pos[1],Z[1]),olib.orbital(0,2,label[2],pos[2],Z[0]),olib.orbital(1,3,label[3],pos[3],Z[1])]
    term = 1

    slab_n = slab(hkl,cells,buff,avec,basis,term)

    
    slab_n.plot_lattice(np.array([b.pos for b in slab_n.slab_base]))
    
    