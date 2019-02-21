#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Small helper utility functions for pyaerocom
"""   
import numpy as np
import os
import multiprocessing as mp
from collections import OrderedDict

class BrowseDict(OrderedDict):
    """Dictionary with get / set attribute methods
    
    Example
    -------
    >>> d = BrowseDict(bla = 3, blub = 4)
    >>> print(d.bla)
    3
    """
    def __getattr__(self, key):
        return self.__getitem__(key)
    
    def __setattr__(self, key, val):
        self.__setitem__(key, val)
        
    def __dir__(self):
        return self.keys()

    def __str__(self):
        return dict_to_str(self)

def check_fun_timeout_multiproc(fun, fun_args=(), timeout_secs=1):
    """Check input function timeout performance
    
    Uses multiprocessing module to test if input function finishes within a 
    certain time interval.
    
    Parameters
    ----------
    fun : callable
        function that is supposed to be tested
    fun_args : tuple
        function arguments
    timeout_secs : float
        timeout in seconds
    
    Returns
    -------
    bool
        True if function execution requires less time than input timeout, else
        False
    """
    
    # Start foo as a process
    OK = True
    p = mp.Process(target=fun, name="test", args=fun_args)
    p.start()
    p.join(timeout_secs)
    if p.is_alive():# Terminate foo
        OK =False
        p.terminate()
        # Cleanup
        p.join()  
    
    return OK   
def _is_interactive():
    import __main__ as main
    return not hasattr(main, '__file__')

def chk_make_subdir(base, name):
    """Check if sub-directory exists in parent directory"""
    d = os.path.join(base, name)
    if not os.path.exists(d):
        os.mkdir(d)
    return d
        
def list_to_shortstr(lst, indent=3):
    """Custom function to convert a list into a short string representation"""
    if len(lst) == 0:
        return "\n" + indent*" " + "[]\n"
    elif len(lst) == 1:
        return "\n" + indent*" " + "[%s]\n" %repr(lst[0])
    s = "\n" + indent*" " + "[%s\n" %repr(lst[0])
    if len(lst) > 4:
        s += (indent+1)*" " + "%s\n" %repr(lst[1])
        s += (indent+1)*" " + "...\n"
        s += (indent+1)*" " + "%s\n" %repr(lst[-2])
    else: 
        for item in lst[1:-1]:
            s += (indent+1)*" " + "%s" %repr(item)
    s += (indent+1)*" " + "%s]\n" %repr(lst[-1])
    return s
        
def dict_to_str(dictionary, s="", indent=3):
    """Custom function to convert dictionary into string (e.g. for print)
    
    Parameters
    ----------
    dictionary : dict
        the dictionary
    s : str
        the input string
    indent : int
        indent of dictionary content
    
    Returns
    -------
    str
        the modified input string
        
    Example
    -------
    
    >>> string = "Printing dictionary d"
    >>> d = dict(Bla=1, Blub=dict(BlaBlub=2))
    >>> print(dict_to_str(d, string))
    Printing dictionary d
       Bla: 1
       Blub (dict)
        BlaBlub: 2
    
    """
    for k, v in dictionary.items():
        if isinstance(v, dict):
            s += "\n" + indent*" " + "{} ({})".format(k, type(v))
            s = dict_to_str(v, s, indent+1)
        elif isinstance(v, list):
            s += "\n" + indent*" " + "{} (list, {} items)".format(k, len(v))
            s += list_to_shortstr(v)
        elif isinstance(v, np.ndarray) and v.ndim==1:
            s += "\n" + indent*" " + "{} (array, {} items)".format(k, len(v))
            s += list_to_shortstr(v)
        else:
            s += "\n" + indent*" " + "{}: {}".format(k, v)
    return s

def str_underline(s, indent=0):
    """Create underlined string"""
    s = indent*" " + "{}\n".format(s)
    s+= indent*" " + "{}".format(len(s)*"-")
    return s

if __name__ == '__main__':
    d = BrowseDict(bla=1, blub=42, blablub=dict(bla=42, blub=43))
    print(d)
