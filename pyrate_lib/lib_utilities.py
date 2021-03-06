#!/usr/bin/env python 
import argparse, os,sys, platform
from numpy import *
import numpy as np
import os, csv, glob
np.set_printoptions(suppress=True) # prints floats, no scientific notation
np.set_printoptions(precision=3)   # rounds all array elements to 3rd digit
import collections
import itertools
from scipy import stats
import lib_DD_likelihood
self_path=os.getcwd()

def rescale_vec_to_range(x, r=1., m=0):
        temp = (x-min(x))/(max(x)-min(x))
        temp = temp*r # rescale
        temp = temp+m # shift
        return(temp)

def calcHPD(data, level=0.95) :
	assert (0 < level < 1)	
	d = list(data)
	d.sort()	
	nData = len(data)
	nIn = int(round(level * nData))
	if nIn < 2 :
		raise RuntimeError("not enough data")	
	i = 0
	r = d[i+nIn-1] - d[i]
	for k in range(len(d) - (nIn - 1)) :
		rk = d[k+nIn-1] - d[k]
		if rk < r :
			r = rk
			i = k
	assert 0 <= i <= i+nIn-1 < len(d)	
	return np.array([d[i], d[i+nIn-1]])


def print_R_vec(name,v):
	new_v=[]
	if len(v)==0: vec= "%s=c()" % (name)
	elif len(v)==1: vec= "%s=c(%s)" % (name,v[0])
	else:
		for j in range(0,len(v)): 
			value=v[j]
			if isnan(v[j]): value="NA"
			new_v.append(value)

		vec="%s=c(%s, " % (name,new_v[0])
		for j in range(1,len(v)-1): vec += "%s," % (new_v[j])
		vec += "%s)"  % (new_v[j+1])
	return vec


def write_ts_te_table(path_dir, tag="",clade=0,burnin=0.1,plot_ltt=True):
	if clade== -1: clade=0 # clade set to -1 by default
	
	direct="%s/*%s*mcmc.log" % (path_dir,tag)
	files=glob.glob(direct)
	files=sort(files)
	if len(files)==0:
		files=[path_dir]
		path_dir = os.path.dirname(path_dir)
		if path_dir=="": path_dir= self_path
		
	print "found", len(files), "log files...\n"
	print files
	print tag
	count=0

	if len(files)==1 or tag != "":
		name_file = os.path.splitext(os.path.basename(files[0]))[0]
		name_file = name_file.split("_mcmc")[0]	
		outfile="%s/%s_se_est.txt" % (path_dir, name_file)
		newfile = open(outfile, "wb") 
		wlog=csv.writer(newfile, delimiter='\t')
		head="clade\tspecies"+ ("\tts\tte"*len(files))
		wlog.writerow(head.split('\t'))
		newfile.flush()

	for f in files:
		try:
			t_file=np.genfromtxt(f, delimiter='\t', dtype=None)
			input_file = os.path.basename(f)
			name_file = os.path.splitext(input_file)[0]
			path_dir = "%s/" % os.path.dirname(f)
			wd = "%s" % os.path.dirname(f)
			shape_f=list(shape(t_file))
			print "%s" % (name_file),
			
			
			if len(files)>1 and tag=="":
				name_file1 = name_file.split("_mcmc")[0]	
				outfile="%s/%s_se_est.txt" % (path_dir, name_file1)
				newfile = open(outfile, "wb") 
				wlog=csv.writer(newfile, delimiter='\t')
				head="clade\tspecies\tts\tte"
				wlog.writerow(head.split('\t'))
				newfile.flush()
				
			
			
			#if count==0:
			head = next(open(f)).split()
			w=[x for x in head if 'TS' in x]
			#w=[x for x in head if 'ts_' in x]
			ind_ts0 = head.index(w[0])
			y=[x for x in head if 'TE' in x]
			#y=[x for x in head if 'te_' in x]
			ind_te0 = head.index(y[0])
			print len(w), "species", np.shape(t_file)
			j=0
			out_list=list()
			if burnin<1: burnin = int(burnin*shape_f[0])
			
			for i in arange(ind_ts0,ind_te0):
				meanTS= mean(t_file[burnin:shape_f[0],i].astype(float))
				meanTE= mean(t_file[burnin:shape_f[0],ind_te0+j].astype(float))
				j+=1
				if count==0: out_list.append(array([clade, j, meanTS, meanTE]))
				else: out_list.append(array([meanTS, meanTE]))
		
				#print i-ind_ts0, array([meanTS,meanTE])
			
			
			out_list=array(out_list)
			
			if plot_ltt is True and count==0:				
				### plot lineages and LTT
				ts = out_list[:,2+count]
				te = out_list[:,3+count]
				print np.shape(ts)
				title = name_file
				time_events=sort(np.concatenate((ts,te),axis=0))[::-1]
				div_trajectory = lib_DD_likelihood.get_DT(time_events,ts,te)

				# R - plot lineages
				out="%s/%s_LTT.r" % (wd,name_file)
				r_file = open(out, "wb") 
	
				if platform.system() == "Windows" or platform.system() == "Microsoft":
					r_script= "\n\npdf(file='%s\%s_LTT.pdf',width=0.6*20, height=0.6*10)\n" % (wd,name_file)
				else: 
					r_script= "\n\npdf(file='%s/%s_LTT.pdf',width=0.6*20, height=0.6*10)\n" % (wd,name_file)
	
				R_ts = print_R_vec("ts",ts)
				R_te = print_R_vec("te",te)
				R_div_trajectory = print_R_vec("div_traj",div_trajectory)
				R_time_events    = print_R_vec("time_events",time_events)

				r_script += """title = "%s"\n%s\n%s\n%s\n%s""" % (name_file,R_ts,R_te,R_div_trajectory,R_time_events)

				r_script += """
				par(mfrow=c(1,2))
				L = length(ts)
				plot(ts, 1:L , xlim=c(-max(ts)-1,0), pch=20, type="n", main=title,xlab="Time (Ma)",ylab="Lineages")
				for (i in 1:L){segments(x0=-te[i],y0=i,x1=-ts[i],y1=i)}	
				t = -time_events
				plot(div_traj ~ t,type="s", main = "Diversity trajectory",xlab="Time (Ma)",ylab="Number of lineages",xlim=c(-max(ts)-1,0))
				abline(v=c(65,200,251,367,445),lty=2,col="gray")
				"""
				
				r_file.writelines(r_script)
				r_file.close()
				print "\nAn LTT plot was saved as: %sLTT.pdf" % (name_file)
				print "\nThe R script with the source for the LTT plot was saved as: %sLTT.r\n(in %s)" % (name_file, wd)
				if platform.system() == "Windows" or platform.system() == "Microsoft":
					cmd="cd %s; Rscript %s\%s_LTT.r" % (wd,wd,name_file)
				else: 
					cmd="cd %s; Rscript %s/%s_LTT.r" % (wd,wd,name_file)
				os.system(cmd)
				print "done\n"
				
				### end plot lineages and LTT
				
			
				
			if count==0: out_array=out_list
			else: out_array=np.hstack((out_array, out_list))
			
			if len(files)>1 and tag=="":
				print shape(out_array)
				for i in range(len(out_array[:,0])):
					log_state=list(out_array[i,:])
					wlog.writerow(log_state)
					newfile.flush()
				print "\nFile saved as:", outfile
				newfile.close()
			else: count+=1
			
		except: print "Could not read file:",name_file
	#print shape(out_array)
	#print out_array[1:5,:]
	if len(files)==1 or tag != "":
		for i in range(len(out_array[:,0])):
			log_state=list(out_array[i,:])
			wlog.writerow(log_state)
			newfile.flush()


		newfile.close()
		print "\nFile saved as:", outfile


# import lib_utilities
# lib_utilities.write_ts_te_table("/Users/daniele/Desktop/try/tries",0)



def calc_marginal_likelihood(infile,burnin,extract_mcmc=1):
	sys.path.append(infile)
	direct="%s/*.log" % infile # PyRateContinuous
	files=glob.glob(direct)
	files=sort(files)
	if len(files)==0:
		print "log files not found."
		quit()
	else: print "found", len(files), "log files...\n"	
	out_file="%s/marginal_likelihoods.txt" % (infile)
	newfile =open(out_file,'wb')
	tbl_header = "file_name\tmodel\tdf"
	for f in files:
		try: 
		#if 2>1:
			t=loadtxt(f, skiprows=max(1,burnin))
			input_file = os.path.basename(f)
			name_file = os.path.splitext(input_file)[0]
			try: replicate = int(name_file.split('_')[-5])
			except: replicate = 0
			#model = name_file.split('_')[-1]
			if "exp.log" in f: model = "Exponential"
			else: model = "Linear"
			
			head = np.array(next(open(f)).split()) # should be faster
			head_l = list(head)
			
			L_index = [head_l.index(i) for i in head_l if "lik" in i]
			
			for i in L_index: tbl_header+= ("\t"+head[i])
			
			if f==files[0]: newfile.writelines(tbl_header)
			
			
			#try:
			#	like_index = np.where(head=="BD_lik")[0][0]
			#except(IndexError): 
			#	like_index = np.where(head=="likelihood")[0][0] 
			try: 
				temp_index = np.where(head=="temperature")[0][0]
			except(IndexError): 
				temp_index = np.where(head=="beta")[0][0]
	
			z=t[:,temp_index] # list of all temps
			y=collections.Counter(z)
			x=list(y) # list of unique values
			x=sort(x)[::-1]
			l=zeros(len(x))
			s=zeros(len(x))
			l_str,s_str="",""
			for like_index in L_index:
				for i in range(len(x)): 
					l[i]=mean(t[:,like_index][(t[:,temp_index]==x[i]).nonzero()[0]]) 
					s[i]=std(t[:,like_index][(t[:,temp_index]==x[i]).nonzero()[0]]) 
					#l_str += "\t%s" % round(l[i],3)
					#s_str += "\t%s" % round(s[i],3)
				mL=0
				for i in range(len(l)-1): mL+=((l[i]+l[i+1])/2.)*(x[i]-x[i+1]) # Beerli and Palczewski 2010
				#ml_str="\n%s\t%s\t%s\t%s%s%s" % (name_file,round(mL,3),replicate,model    ,l_str,s_str)
				n_categories = len(x)
				if like_index == min(L_index): ml_str="\n%s\t%s\t%s\t%s" % (name_file,model,n_categories,round(mL,3))
				else: ml_str += "\t%s" % (round(mL,3))
			newfile.writelines(ml_str)
			
			if extract_mcmc==1:
				out_name="%s/%s_cold.log" % (infile,name_file)
				newfile2 =open(out_name,'wb')
				
				t_red = t[(t[:,temp_index]==1).nonzero()[0]]
				newfile2.writelines( "\t".join(head_l)  )
				for l in range(shape(t_red)[0]):
					line= ""
					for i in t_red[l,:]: line+= "%s\t" % (i)
					newfile2.writelines( "\n"+line  )
				#
				#l[i]=mean(t[:,like_index][(t[:,temp_index]==x[i]).nonzero()[0]]) 
			        #
				newfile2.close()
			
			
			
			
			sys.stdout.write(".")
			sys.stdout.flush()
		except:
			print "\n WARNING: cannot read file:", f, "\n\n"

	newfile.close()



def parse_hsp_logfile(logfile,burnin=100):
	t=np.loadtxt(logfile, skiprows=max(1,burnin))
	head = next(open(logfile)).split()
	
	baseline_L = mean(t[:,4])
	baseline_M = mean(t[:,5])
		
	l_indexL = [head.index(i) for i in head if "Gl" in i]
	l_indexM = [head.index(i) for i in head if "Gm" in i]
	
	C = list(head[4])
	fixed_focal_clade = ""
	for i in range(1,len(C)):
		fixed_focal_clade+=C[i]
	
	fixed_focal_clade = int(fixed_focal_clade) 
	k_indexL = [head.index(i) for i in head if "kl" in i]
	k_indexM = [head.index(i) for i in head if "km" in i]
	
	gl,gm,kl,km = list(),list(),list(),list()
	for i in range(len(l_indexL)):
		gl.append(mean(t[:,l_indexL[i]]))
		kl.append(mean(t[:,k_indexL[i]]))
		gm.append(mean(t[:,l_indexM[i]]))
		km.append(mean(t[:,k_indexM[i]]))
	
	return(fixed_focal_clade,baseline_L,baseline_M,np.array(gl),np.array(gm),np.array(kl),np.array(km))
 


def parse_hsp_logfile_HPD(logfile,burnin=100):
	t=np.loadtxt(logfile, skiprows=max(1,burnin))
	head = next(open(logfile)).split()
	
	# get col indexes
	L0_index = 4
	M0_index = 5
	l_indexL = [head.index(i) for i in head if "Gl" in i]
	l_indexM = [head.index(i) for i in head if "Gm" in i]
	k_indexL = [head.index(i) for i in head if "kl" in i]
	k_indexM = [head.index(i) for i in head if "km" in i]
	
	# get number of focal clade
	C = list(head[L0_index])
	fixed_focal_clade = ""
	for i in range(1,len(C)):  # so if head[L0_index]== "l12": C=["l","1","2"] and fixed_focal_clade = "12"
		fixed_focal_clade+=C[i]
	
	fixed_focal_clade = int(fixed_focal_clade) 
	
		
	print "\nGetting posterior parameter values..."
	# store l0,m0,gl,gm values for each MCMC iteration
	L0_list,M0_list,gl_list,gm_list = list(),list(),list(),list()

	for j in range(shape(t)[0]):
		# baseline rates
		L0 = t[j,L0_index]
		M0 = t[j,M0_index]
		# G parameters
		gl = t[j,l_indexL]
		gm = t[j,l_indexM]
		
		L0_list.append(L0)
		M0_list.append(M0)
		gl_list.append(gl)
		gm_list.append(gm)

	L0_list = np.array(L0_list)
	M0_list = np.array(M0_list)
	gl_list = np.array(gl_list)
	gm_list = np.array(gm_list)
	#print np.shape(gl_list)
	
	# get posterior estimate of k
	kl,km = list(),list()
	for i in range(len(l_indexL)):
		kl.append(mean(t[:,k_indexL[i]]))
		km.append(mean(t[:,k_indexM[i]]))
	
	gl,gm = list(),list()
	for i in range(len(l_indexL)):
		gl.append(mean(t[:,l_indexL[i]]))
		gm.append(mean(t[:,l_indexM[i]]))
	
	return(fixed_focal_clade,L0_list,M0_list,gl_list,gm_list,np.array(kl),np.array(km))


def get_mode(data):
	# determine bins Freedman-Diaconis rule
	iqr = np.subtract(*np.percentile(data,[75,25])) # interquantile range
	h_temp = 2 * iqr * len(data) **(-1./3) # width
	h = max(h_temp,0.0001)
	n_bins= int((max(data)-min(data))/h)
	hist=np.histogram(data,bins=n_bins)
	return hist[1][np.argmax(hist[0])] # modal value



#### CHECK TAXA NAMES FOR TYPOS
def calc_diff_string(a,b):
	s = a==b
	score = np.float(len(s[s == True]))/len(s)
	s_diff = len(s[s == False])
	return score, s_diff
	
def get_score(a,b,max_length_diff):
	if a==b is True: score = 1
	else:
		a=a.lower() 
		b=b.lower() 
		if a==b is True: score = 1 # no matter upper/lower case
		else:
			a1 = np.array(list(a))
			b1 = np.array(list(b))
			if len(a1)==len(b1): # if same length assume no missing/extra letters
				score, s_diff = calc_diff_string(a1,b1)
			elif np.abs(len(a1)-len(b1)) > max_length_diff:
				score, s_diff = 0, len(b1)
			else:
				l_a =a1[np.array(list(itertools.combinations(np.arange(len(a1)),min(len(a1),len(b1)))))]
				l_b =b1[np.array(list(itertools.combinations(np.arange(len(b1)),min(len(a1),len(b1)))))]
				s = l_a==l_b
				s_bin = s.astype(None) # convert True/False array into 1/0 array
				score = np.max(np.sum(s_bin,axis=1))/np.mean([len(a1),len(b1)])
				s_diff = np.abs(len(a1)-len(b1)) + ( min(len(a1),len(b1)) - np.max(np.sum(s_bin,axis=1)) )
	if score==1: s_diff=0
	return score, s_diff

def check_taxa_names(SpeciesList_file):
	w=np.genfromtxt(SpeciesList_file, dtype=str)[:,0]
	words = np.unique(w)
	print "\nTaxa names with possible misspells (if any) will be listed below..."
	word_combinations = itertools.combinations(words,2)
	
	# sensitivity settings
	max_length_diff = 2 # maximum allowed difference between string lengths
	threshold_score = 0.7
	threshold_s_diff = 3
	all_scores = []

	for w in word_combinations: 
		taxon1 = w[0]
		taxon2 = w[1]
		score_all, diff_all = get_score(taxon1,taxon2,max_length_diff)
		# GENUS
		a = taxon1.split("_")[0]
		b = taxon2.split("_")[0]
		score_genus, diff_genus = get_score(a,b,max_length_diff)
		# SPECIES
		if len(taxon1.split("_"))>1 and len(taxon2.split("_"))>1:
			a = taxon1.split("_")[1]
			b = taxon2.split("_")[1]
			score_species, diff_species = get_score(a,b,max_length_diff)
		else: score_species, diff_species = score_genus,0	
		s_diff = diff_genus+diff_species	
		if (score_genus+score_species)<2:
			if score_all > threshold_score and diff_all <= threshold_s_diff:
				if np.mean([score_genus,score_species]) > threshold_score and s_diff <= threshold_s_diff:
					all_scores.append([taxon1, taxon2,round(score_all,3),round(score_genus,3),
					round(score_species,3),int(s_diff)])

	all_scores = np.array(all_scores)
	# top hits:
	score_float = all_scores[:,2].astype(float)
	diff_int    = all_scores[:,5].astype(int)
	if len(all_scores)==0: sys.exit("No typos found!")
	th1,th2 = 0.9,1
	passed = np.array([])
	while True:
		pass1 = (score_float>th1).nonzero()[0]
		pass2 = (diff_int<=th2).nonzero()[0]
		res = np.union1d(pass1,pass2)
		for i in res: 
			if i not in passed: 
				print '\t'.join(all_scores[i])
		if len(res)==0: print "No typos found!"
		passed = np.union1d(res,passed)
		if len(passed)==len(all_scores): break
		answ = raw_input("\nShow more results using lower threshold (y or n)? ")
		if answ=="y":
			th1 -= 0.1
			th2 += 1
		else: break




def reduce_log_file(log_file,burnin=1): # written by Tobias Hofmann (tobias.hofmann@bioenv.gu.se)
	print log_file
	target_columns = ["it","posterior","prior","PP_lik","BD_lik","q_rate","alpha","k_birth","k_death","root_age","death_age"]
	workdir = os.path.dirname(log_file)
	if workdir=="": workdir= self_path
	input_file = os.path.basename(log_file)
	name_file = os.path.splitext(input_file)[0]
	outfile = "%s/%s_reducedLog.log" %(workdir,name_file)
	output = open(outfile, "wb")
	outlog=csv.writer(output, delimiter='\t')
	print "Parsing header..."
	head = next(open(log_file)).split()
	w=[head.index(x) for x in head if x in target_columns]
	print w
	print "Reading mcmc log file..."
	#log_file = "%s" % (log_file)
	print log_file
	tbl = np.loadtxt(log_file,skiprows=burnin,usecols=(w))
	print np.shape(tbl)	
	outlog.writerow(target_columns)
	for i in tbl: outlog.writerow(list(i))
	print "The reduced log file was saved as: %s\n" % (outfile)
	
