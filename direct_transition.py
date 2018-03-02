# -*- coding: utf-8 -*-
"""
Created on Thu Mar  1 11:53:08 2018

@author: rday
"""

import numpy as np
import matplotlib.pyplot as plt
import Ylm
import adaptive_int as adint
import sympy.physics.wigner as wig
import klib as K_lib
import matplotlib.cm as cm

kb = 1.38*10**-23
q = 1.602*10**-19

class direct:
    
    def __init__(self,Adict):
        self.TB = Adict['TB']
        self.hv = Adict['hv']
        self.pol = Adict['pol']
        self.T = Adict['T']
        self.TB = Adict['TB']
        self.Gamma = Adict['Gamma']
        
        cube = Adict['cube']
        xv,yv,self.kz,Ev = cube['X'],cube['Y'],cube['kz'],cube['E']
        self.x = np.linspace(*xv)
        self.y = np.linspace(*yv)
        
        self.X,self.Y = np.meshgrid(self.x,self.y)
        self.Earr = np.linspace(*Ev)
        self.Tmat = self.direct_mat(self.Baa(),self.Gaau())
        
    def Baa(self):
        '''
        Compute an array of radial integrals for the following matrix element: <Psi_f|E.r|Psi_f>
        
                           /\ Rmax
                          |         3
        B_n1_l1_n2_l2 =   |   dr   r  R(r) x R(r)   
                          |             n1l1  n2l2
                      0 \/   
        args: self -- use the orbital basis defined in the __init__ above
        return: numpy array (len(basis)xlen(basis)) of float
        '''
        Bmat = np.zeros((len(self.TB.basis),len(self.TB.basis)))
        integral_dict = {}
        tol = 10**-8
        for b1 in self.TB.basis:
            for b2 in self.TB.basis:
                o_str = '{:d},{:d},{:d},{:d}'.format(b1.n,b2.n,b1.l,b2.l)
                try:
                    integral_dict[o_str]
                except KeyError:
                    trueconverge = False
                    rmax = 10.0
                    while not trueconverge:
                        integral_dict[o_str] = adint.direct_integrate(0.0,rmax,tol,[b1.Z,b2.Z],[b1.label,b2.label])
                        if abs(integral_dict[o_str])<10**-10:
                            rmax/=2.0
                        else:
                            trueconverge = True
                Bmat[b1.index,b2.index] = integral_dict[o_str]
                Bmat[b2.index,b1.index] = integral_dict[o_str]
        return Bmat
    
    def Gaau(self):
        '''
        Compute the angular integrals for the direct transition matrix element <Psi_f|E.r|Psi_f>
                           /\
                          |         
        G_l1_m1_l2_mu =   |   dadb   Y*(a,b) x Y(a,b) x Y(a,b)
                          |           l2,m1+mu   1,mu     l1,m1
                        \/   
        
        args: self -- use the same basis as defined above in __init__
        return: numpy array (len(basis)xlen(basis)x3) of float, one for each mu (-1,0,1)
        '''
        Gmat = np.zeros((len(self.TB.basis),len(self.TB.basis),3),dtype=complex)
        integral_dict = {}
        for b1 in self.TB.basis:
            for b2 in self.TB.basis:
                if b1.index<=b2.index:
                    if b1.spin==b2.spin:
                        for mu in range(-1,2):
                            o_str = '{:s},{:s},{:d}'.format(b1.label[1:],b2.label[1:],mu)
                            try:
                                integral_dict[o_str]
                            except KeyError:
                                integral_dict[o_str]=0.0j
                                for p1 in b1.proj:
                                    for p2 in b2.proj:
                                        integral_dict[o_str] += (p1[0]+1.0j*p1[1])*(p2[0]-1.0j*p2[1])*float(wig.clebsch_gordan(b1.l,1,b2.l,0,0,0))*float(wig.clebsch_gordan(b1.l,1,b2.l,p1[2],mu,p2[2]))*np.sqrt((2*b1.l+1)/(2*b2.l+1))
                                
                            Gmat[b1.index,b2.index,mu+1] = integral_dict[o_str]
                            Gmat[b2.index,b1.index,mu+1] = np.conj(integral_dict[o_str])
        return Gmat

    def direct_mat(self,B,G):
        ''' compute the product of the two matrices defined above
        return array (same size as G) of float
        '''
        return np.dot(B,G)
    
    
    def resonant_intensity(self):

        self.diagonalize(self.X,self.Y,self.kz)
        Beta =1./kb*self.T/q
        ##cube_indx is the position in the 3d cube of K and energy where this band is
        fv = vf(self.Eb*Beta)
        farr = vf(self.Earr*Beta) 
        polv = pol_2_sph(self.pol)
        Tm = np.dot(self.Tmat,polv)
        
        Mk = np.zeros((len(self.x),len(self.y),len(self.Earr)))
        u=np.linspace(0,len(self.TB.basis)-1,len(self.TB.basis)).astype(int)
        U,V=np.meshgrid(u,u)
        '''
        This loop needs figuring out!
        '''
        TP_max = lineshape(self.hv,self.hv,self.Gamma)
        TP_abs_max = 0.0
        TP_abs_min = 0.0
        tp = np.zeros((np.shape(self.X)[0],np.shape(self.X)[1],len(self.TB.basis),len(self.TB.basis)))
        
        for i in range(np.shape(self.X)[0]):
            for j in range(np.shape(self.X)[1]): 
                for v in range(len(self.TB.basis)):
                    for u in range(len(self.TB.basis)):
                        
                        trans = 2.0/np.pi*abs(np.dot(np.conj(self.Ev[i,j,:,u]),np.dot(Tm,self.Ev[i,j,:,v])))**2*dfermi(fv[i,j,v],fv[i,j,u])*lineshape(self.Eb[i,j,u]-self.Eb[i,j,v],self.hv,self.Gamma)/TP_max
#                        if trans.max()>TP_abs_max:
#                            TP_abs_max = trans.max()
#                            print(trans.max())
                        Mk[i,j,:]+=trans*np.imag(-1./(np.pi*(self.Earr-self.Eb[i,j,u]+0.02j))) -trans*np.imag(-1./(np.pi*(self.Earr-self.Eb[i,j,v]+0.02j)))

#        print('maxx',TP_abs_max)
#        for v in range(len(self.TB.basis)):
#            for u in range(len(self.TB.basis)):
#                Mk += np.sum(tp[:,:,u,v]*np.imag(np.imag(-1./(self.Earr-self.Eb[:,:,u]+0.02j)))) + (farr*(1-tp[:,:,u,v]))*np.imag(-1./(self.Earr-self.Eb[:,:,v]+0.02j))
##                        Mk[i,j,:] += trans_prob*(np.imag(-1./(self.Earr-self.Eb[i,j,u]+0.02j))-np.imag(-1./(self.Earr-self.Eb[i,j,v]+0.02j)))
#                    Mk[i,j,:] += np.imag(-1./np.pi*((self.Earr-self.Eb[i,j,v]+0.02j)))*farr

        fig = plt.figure()
        ax = fig.add_subplot(111)
        E,K = np.meshgrid(self.Earr,self.x)
        p = ax.pcolormesh(E,K,Mk[:,int(np.shape(Mk)[1]/2),:],cmap=cm.bwr)
        plt.colorbar(p,ax=ax)
        
        return Mk
        
        
    def diagonalize(self,X,Y,kz):
        self.X = X
        self.Y = Y
        self.kz = kz
        
        k_arr,_ = K_lib.kmesh(0.0,self.X,self.Y,self.kz)      
    
        self.TB.Kobj = K_lib.kpath(k_arr)
        self.Eb,self.Ev = self.TB.solve_H()
        #self.Eb has shape (len(K),len(base))
        #self.Evec has shape(len(K),len(base),len(base))
        self.Eb = np.reshape(self.Eb,(np.shape(X)[0],np.shape(X)[1],len(self.TB.basis)))
        self.Ev = np.reshape(self.Ev,(np.shape(X)[0],np.shape(X)[1],len(self.TB.basis),len(self.TB.basis)))
        
def lineshape(w,wo,Gamma):
    return Gamma/(2*((w-wo)**2+Gamma**2/4))
                
        
def pol_2_sph(pol):
    '''
    return pol vector in spherical harmonics -- order being Y_11, Y_10, Y_1-1
    '''
    M = np.sqrt(0.5)*np.array([[-1,1.0j,0],[0,0,np.sqrt(2)],[1.,1.0j,0]])
    return np.dot(M,pol)

def con_ferm(x):      ##Typical energy scales involved and temperatures involved give overflow in exponential--define a new fermi function that works around this problem
    tmp = 0.0
    if x<709:
        tmp = 1.0/(np.exp(x)+1)
    return tmp

def dfermi(f1,f2):
    return f1-f2 if (f1-f2)>0 else 0


vf = np.vectorize(con_ferm)
                    

