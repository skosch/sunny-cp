'''
sunny-cp: a CP portfolio solver consisting of 12 constituent solvers:

  Choco, Chuffed, CPX, G12/LazyFD, G12/FD, G12/Gurobi, 
  G12/CBC, Gecode, HaifaCSP, iZplus, MinisatID, OR-Tools

********************************************************************************
* Note that the MiniZinc model in input MUST NOT contain the reserved keyword  *
* o__b__j__v__a__r and the output produced is not formatted (it is possible to *
* use the solns2out tool of MiniZinc suite to format the output)               *
********************************************************************************
* Don't forget to properly set the SUNNY_HOME and PATH environment variables!! *
********************************************************************************
  
Usage: sunny-cp [OPTIONS] <MODEL.mzn> [DATA.dzn] 

FIXME: CHANGE THIS DOCUMENTATION!!!

Options:

  -h, --help  		
    Print this message
    
  -T <timeout>
    Timeout (in seconds) of SUNNY algorithm. Note that this IS NOT the timeout 
    of the whole solving process: if the instance is still not solved within T 
    seconds by the scheduled solvers, the others non-scheduled solvers of the 
    portfolio will be executed for T seconds following a default ordering. 
    Anyway, note that none of the solvers will be executed for more than T 
    seconds.
    The default value is T = 1800, while the default 'backup' ordering is:
      chuffed, g12cpx, minisatid, gecode, g12lazyfd, g12fd, g12gurobi, g12cbc    
  
  -k <size>
    Neighborhood size of SUNNY underlying k-NN algorithm. The default value of 
    k is 70, while the distance metric is the Euclidean one
  
  -P <portfolio>
    Specifies the portfolio through a comma-separated list of solvers of the 
    form s_1,s_2,...,s_m. Note that such solvers must be a not empty subset of 
    the default portfolio. Moreover, also the specified ordering of solvers is 
    important: indeed, in case of failure of the scheduled solvers, the other 
    solvers will be executed according to such ordering. This option can be used 
    to select a particular sub-portfolio or even to change the default ordering 
    of the solvers in case of failures
  
  -b <solver>
    Set the backup solver of the portfolio. The default backup solver is chuffed
    
  -K <path>
    Absolute path of the folder which contains the knowledge base. The default 
    knowledge base is in SUNNY_HOME/kb/all_T1800. For more details, see the 
    README file in SUNNY_HOME/kb folder
  
  -s <schedule>
    Specifies a static schedule to be run before executing the SUNNY algorithm 
    on a given COP. The schedule must be passed in the form: 
      s_1,t_1,s_2,t_2,...,s_m,t_m
    where each s_i belongs to the specified portfolio, 0 < t_i <= T, and 
    C = t_1 + ... + t_m <= T, where T is the specified solving timeout for COPs. 
    Passing a static schedule has the purpose of providing a 'warm start' to the 
    SUNNY algorithm in the first C seconds: first s_1 is run for t_1 seconds, 
    then s_2 is run for t_2 seconds, ..., and finally s_m is run for t_m seconds 
    by exploiting each sub-optimal solution found by the previous solver. If the 
    problem is still not solved after running the static schedule, the schedule 
    resulting from SUNNY algorithm is run in the remaining T - C seconds. The 
    static schedule is empty by default
    
  -d <path> 
    Absolute path of the folder in which the temporary files created by the 
    solver will be put. The default directory is SUNNY_HOME/tmp, and by default 
    such files are deleted after sunny-cp execution
    
  --keep
    Do not erase the temporary files created by the solver and stored in the 
    specified directory. This option is unset by default.
'''

import sys
import getopt
from string import replace
from defaults import *
  
def parse_arguments(args):
  """
  Parse the input arguments and returns the corresponding values.
  """
  
  # Get the arguments and parse the input model to get auxiliary information. 
  mzn, dzn, opts = get_args(args)
  k, T, pfolio, backup, kb, lims, \
  static, obj, obj_var, out_mzn = parse_model(mzn)
 
  # Arguments parsing.
  for o, a in opts:
    if o in ('-h', '--help'):
      print __doc__
      sys.exit(0)
    # FIXME: Manage better -a and -p options:
    elif o == '-a':
      if obj == 'sat':
	print >> sys.stderr, 'Warning: ignoring -a option'
    elif o == '-p':
      print >> sys.stderr, 'Warning: ignoring -p option (parallel solving ' \
                           'not yet implemented, -p is fixed to 1)'
    elif o == '-k':
      k = int(a)
      if k < 0:
	print >> sys.stderr, 'Error! Negative value ' + a + ' for k value.'
	print >> sys.stderr, 'For help use --help'
	sys.exit(2)
    elif o == '-T':
      T = int(a)
      if T <= 0:
	print >> sys.stderr, 'Error! Non-positive value ' + a + ' for timeout.'
	print >> sys.stderr, 'For help use --help'
	sys.exit(2)
    elif o == '-P':
      p = a.split(',')
      if not p:
	print >> sys.stderr, \
	'Error! The portfolio ' + a + ' is not valid.'
	print >> sys.stderr, 'For help use --help'
	sys.exit(2)
      if not set(p) <= set(pfolio):
	print >> sys.stderr, \
	'Error! The portfolio ' + a + ' is not a subset of ' + str(pfolio)
	print >> sys.stderr, 'For help use --help'
	sys.exit(2)
      pfolio = p
    elif o == '-b':
      backup = a
    elif o == '-K':
      if not os.path.exists(a):
	print >> sys.stderr, 'Error! Directory ' + a + ' not exists.'
	print >> sys.stderr, 'For help use --help'
	sys.exit(2)
      name = [token for token in a.split('/') if token][-1]
      if a[-1] != '/':
	path = a + '/'
      else:
	path = a
      if obj in ['min', 'max']:
	pb = 'cop'
      else:
        pb = 'csp'
      kb = path + 'kb_' + pb + '_' + name
      lims = path + 'lims_' + pb + '_' + name
      if not os.path.exists(kb):
	print >> sys.stderr, 'Error! File ' + kb + ' not exists.'
	print >> sys.stderr, 'For help use --help'
	sys.exit(2)
      if not os.path.exists(lims):
	print >> sys.stderr, 'Error! File ' + kb + ' not exists.'
	print >> sys.stderr, 'For help use --help'
	sys.exit(2)
    elif o == '-s':
      s = a.split(',')
      for i in range(0, len(s) / 2):
	static.append((s[2 * i], int(s[2 * i + 1])))
    elif o == '-d':
      if not os.path.exists(a):
	print >> sys.stderr, 'Error! Directory ' + a + ' not exists.'
	print >> sys.stderr, 'For help use --help'
	sys.exit(2)
      name = [token for token in a.split('/') if token][-1]
      if a[-1] == '/':
	TMP_DIR = a[0 : -1]
      else:
	TMP_DIR = a
    elif o == '--keep':
      KEEP = True
      
  # Additional checks.
  if backup not in pfolio:
    print >> sys.stderr, \
    'Error! Backup solver ' + backup + ' is not in ' + str(pfolio)
    print >> sys.stderr, 'For help use --help'
    sys.exit(2)
  if not (set(s for (s, t) in static) <= set(pfolio)):
    print >> sys.stderr, \
    'Error! Static schedule is not a subset of ' + str(pfolio)
    print >> sys.stderr, 'For help use --help'
    sys.exit(2)
  st = 0
  for (s, t) in static:
    st += t
    if t <= 0 or t > T:
      print >> sys.stderr, \
      'Error! Not valid time slot ' + t + ' for static schedule'
      print >> sys.stderr, 'For help use --help'
      sys.exit(2)
    if s not in pfolio:
      print >> sys.stderr, 'Error! Solver ' + s + ' is not in ' + str(pfolio)
      print >> sys.stderr, 'For help use --help'
      sys.exit(2)
  if st > T:
    print >> sys.stderr, \
    'Error! Static schedule allocated time exceeds the timeout'
    print >> sys.stderr, 'For help use --help'
  return mzn, dzn, obj, obj_var, out_mzn, k, T, pfolio, backup, kb, lims, static

def get_args(args):
  """
  Get the arguments.
  """
  dzn = ''
  try:
    opts, args = getopt.getopt(
      args, 'ahT:k:P:b:K:s:d:p:', ['help', 'keep']
    )
  except getopt.error, msg:
    print msg
    print >> sys.stderr, 'For help use --help'
    sys.exit(2)
  
  if len(args) == 0:
    for o, a in opts:
      if o in ('-h', '--help'):
        print __doc__
        sys.exit(0)
    print >> sys.stderr, 'Error! No arguments given.'
    print >> sys.stderr, 'For help use --help'
    sys.exit(2)
  mzn = args[0]
  if not mzn.endswith('.mzn'):
    print >> sys.stderr, 'Error! MiniZinc input model must have .mzn extension.'
    print >> sys.stderr, 'For help use --help'
    sys.exit(2)
  if len(args) > 1:
    dzn = args[1]
    if not dzn.endswith('.dzn'):
      print >> sys.stderr, \
      'Error! MiniZinc input data must have .dzn extension.'
      print >> sys.stderr, 'For help use --help'
      sys.exit(2)
  return mzn, dzn, opts

def parse_model(mzn):
  """
  Parse the input model to get auxiliary information (e.g., objective function).
  """
  # Set default arguments.
  k = DEF_k_csp
  T = DEF_T_csp
  pfolio = DEF_pfolio_csp
  backup = DEF_backup_csp
  kb = DEF_kb_csp
  lims = DEF_lims_csp
  static = DEF_static_csp
  obj = 'sat'
  solve_item = False
  output_item = False
  include_list = [mzn]
  out_mzn = None
  static = []
  obj_var = ''
  mzn_dir = os.path.dirname(mzn)
  
  # Possibly extract solve and output items (for COPs).
  while include_list and not (solve_item and output_item):
    model = include_list.pop()
    if os.path.exists(model):
      lines = open(model, 'r').read().split(';')
    elif os.path.exists(mzn_dir + '/' + model):
      model = mzn_dir + '/' + model
      lines = open(model, 'r').read().split(';')
    else:
      continue
    for line in lines:
      include = False
      new_line = ''
      ignore = False
      for l in line:
	# Ignore comments.
        if ignore or l == '%':
          ignore = True
          if l == '\n':
            ignore = False
        else:
          new_line += l
      tokens = new_line.split()
      i = 0
      for token in tokens:
        if token == 'include' or token == 'include"':
          include = True
        # Looking for included models.
        if include and token[-1] == '"' or token[-1] == '";':
	  include = \
	    replace(replace(replace(token, 'include"', ''),'"', ''), "'", '')
	  include_list.append(include)
          include = False
	elif token.endswith('satisfy'):
	  include_list = []
	  break
	elif token in ['minimize', 'maximize']:
	  solve_item = True
	  k = DEF_k_cop
	  T = DEF_T_cop
	  pfolio = DEF_pfolio_cop
	  backup = DEF_backup_cop
	  kb = DEF_kb_cop
	  lims = DEF_lims_cop
	  static = DEF_static_cop
	  if token == 'minimize':
	    obj = 'min'
	  else:
	    obj = 'max'
          obj_var = ''
          for j in range(i + 1, len(tokens)):
	    obj_var += tokens[j] + ' '
	  if output_item:
	    include_list = []
	    break
	elif token in ['output', 'output[']:
	  out_mzn = model
          output_item = True
	  if solve_item:
	    include_list = []
	    break
        i += 1
  return k, T, pfolio, backup, kb, lims, static, obj, obj_var, out_mzn