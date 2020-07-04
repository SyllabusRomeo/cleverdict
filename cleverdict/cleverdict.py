import keyword
import itertools

__version__ = "1.5.1"

'''
Change log
==========
version 1.5.1  2020-07-02
-------------------------
First version with the change log.

Removed the no_expand context manager and introduced a more logical expand context manager. The context
manager now restores the CleverDict.expand setting correctly upon exiting.

Expansion can now be controlled by CleverDict.expand, instead of cleverdict.expand.

The __repr__ method now provides the vars as well, thus showing attributes set with set_attr_direct also
The __repr__ method output is more readable

In order to support evalation from __repr__, the __init__ method has been changed.

The implemenation of several methods is more compact and more stable by reusing functionality.

More and improved tests.
'''

class expand:
    def __init__(self, ok):
        """
        provides a context manager to temporary disable expansion of keys.
        upon exiting the context manager, the value of expand is restored.
        
        Parameters
        ----------
        ok : bool
           if True, enabled expansion
           if False, disable expansion
        """
        self.ok = ok

    def __enter__(self):
        self.save_expand = CleverDict.expand
        CleverDict.expand = self.ok

    def __exit__(self, *args):
        CleverDict.expand = self.save_expand


def name_to_aliases(name):
    """
    return all possible aliases for name

    Parameters
    ----------
    name : any
    
    Return
    ------
    Aliases for name : list
        if CleverDict.expand == False (preferable set via the expand context manager, 
        the list will contain only name
        otherwise (default), the list will start with the name, followed by all possible aliases for name      
    """
    result = [name]
    if CleverDict.expand:
        if name == hash(name):
            result.append(f"_{int(name)}")
            if name in (0, 1):
                result.append(f"_{bool(name)}")
        else:
            if name != str(name):
                name = str(name)
                if name.isidentifier() and not keyword.iskeyword(name):
                    result.append(str(name))

            if not name or name[0].isdigit() or keyword.iskeyword(name):
                norm_name = "_" + name
            else:
                norm_name = name

            norm_name = "".join(ch if ("A"[:i] + ch).isidentifier() else "_" for i, ch in enumerate(norm_name))
            if name != norm_name:
                result.append(norm_name)
    return result

class CleverDict(dict):
    """
    A data structure which allows both object attributes and dictionary
    keys and values to be used simultaneously and interchangeably.

    The save() method (which you can adapt or overwrite) is called whenever
    an attribute or dictionary value changes.  Useful for automatically writing
    results to a database, for example:

        from cleverdict.test_cleverdict import my_example_save_function
        CleverDict.save = my_example_save_function

    Convert an existing dictionary or UserDict to CleverDict:
        x = CleverDict(my_existing_dict)

    Import data from an existing object to a CleverDict:
        x = CleverDict(vars(my_existing_object))

    Created by Peter Fison, Ruud van der Ham, Loic Domaigne, and Rik Huygen
    from pythonistacafe.com, hoping to improve on a similar feature in Pandas.
    """
    expand = True

    def __init__(self, _mapping=(), _aliases=None, _vars={}, **kwargs):
        self.setattr_direct("_aliases", {})
        with expand(CleverDict.expand if _aliases is None else False):
            self.update(_mapping, **kwargs)
            if _aliases is not None:
                for k, v in _aliases.items():
                    self._add_alias(v, k)
            for k, v in _vars.items():
                self.setattr_direct(k, v)            

    def update(self, _mapping=(), **kwargs):
        if hasattr(_mapping, "items"):
            _mapping = getattr(_mapping, "items")()
        
        for k, v in itertools.chain(_mapping, getattr(kwargs, "items")()):
            self.__setitem__(k, v)
                

    @classmethod
    def fromkeys(cls, keys, value):
        return CleverDict({k: value for k in keys})

    def save(self, name, value):
        pass

    def __setattr__(self, name, value):
        if name in self._aliases:
            name = self._aliases[name]
        elif name not in self:
            for al in name_to_aliases(name):
                self._add_alias(name, al)
        super().__setitem__(name, value)
        self.save(name, value)        

    __setitem__ = __setattr__

    def setattr_direct(self, name, value):
        """
        Sets an attribute directly, i.e. without making it into an item.
        This can be useful to store save data.

        Used internally to create the _aliases dict.

        Parameters
        ----------
        name : str
            name of attribute to be set

        value : any
            value of the attribute

        Returns
        -------
        None
        """

        super().__setattr__(name, value)

    def __getitem__(self, name):
        name = self.get_key(name)
        return super().__getitem__(name)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(e)

    def __delitem__(self, key):
        key = self.get_key(key)
        super().__delitem__(key)
        for ak, av in list(self._aliases.items()):
            if av == key:
                del self._aliases[ak]

    def __delattr__(self, k):
        try:
            del self[k]
        except KeyError as e:
            raise AttributeError(e)

    def get_key(self, name):
        """
        gets key where name is belonging to
        
        Parameters
        ----------
        name : any
            name to be searched
            
        Returns
        -------
        key where name belongs to : any
        
        Notes
        -----
        If name can't be found, a KeyError is raised
        """
        if name in self._aliases:
            return self._aliases[name]
        raise KeyError(name)

    _default = object()

    def get_aliases(self, name=_default):
        """
        get all alliases or aliases for a given name
        
        Parameters
        ----------
        name : any
            name to be given aliases for
            if omitted, all aliases will be returned
        
        Returns
        -------
        aliases : list
            list of aliases
        """
        if name is CleverDict._default:
            return list(self._aliases.keys())
        else:            
            return [ak for ak, av in self._aliases.items() if av == self.get_key(name)]

    def add_alias(self, name, alias):
        """
        adds an alias to a given key
        
        Parameters
        ----------
        name : any
            must be an existing key or an alias
            
        alias : scalar or list of scalar
            alias(es) to be added to the key
            
        Returns
        -------
        None
        
        Notes
        -----
        If alias is already refering to a key belonging to name, this is dummy
        If alias is already refering to key not belonging to name, a KeyError will be raised        
        """

        key = self.get_key(name)
        if not hasattr(alias, "__iter__") or isinstance(alias, str):
            alias = [alias]
        for al in alias:
            for name in name_to_aliases(al):
                self._add_alias(key, name)

    def _add_alias(self, name, alias):
        """
        internal method
        """
        if alias in self._aliases and self._aliases[alias] != name:
            raise KeyError(f"{repr(alias)} already an alias for {repr(self._aliases[alias])}")
        self._aliases[alias] = name

    def delete_alias(self, alias):
        """
        deletes an alias 
        
        Parameters
        ----------
        alias : scalar or list of scalars
            alias(es) to be deleted
            
        Returns
        -------
        None
        
        Notes
        -----
        if CleverDict.expand is True (the 'normal' case), all aliases (apart from the key that refer to alias
            are deleted as well (if they exist))
        if CleverDict.expand is False (most likely set the expand context manager), only alias will be deleted
        
        Keys cannot be deleted
        """
        if not hasattr(alias, "__iter__") or isinstance(alias, str):
            alias = [alias]
        for al in alias:
            if al not in self._aliases:
                raise KeyError(f"{repr(al)} not present")
            if al in self:
                raise KeyError(f"key element {repr(al)} can't be deleted")
            del self._aliases[al]
            for alx in name_to_aliases(al):
                if alx in list(self._aliases.keys())[1:]:  # ignore the key, which is at the front of ._aliases
                    del self._aliases[alx]


    def __repr__(self):
       _mapping = dict(self.items())
       _aliases = {k: v for k, v in self._aliases.items() if k not in self}
       _vars = {k: v for k,v in vars(self).items() if k != '_aliases'}
       return f"{self.__class__.__name__}({repr(_mapping)}, _aliases={repr(_aliases)}, _vars={repr(_vars)})"

    def __str__(self):
        result = [__class__.__name__]
        id = "x"
        for k, v in self.items():
            parts = ["    "]

            with expand(True):
                for ak in name_to_aliases(k):
                    parts.append(f"{id}[{repr(ak)}] == ")
                for ak in name_to_aliases(k):
                    if isinstance(ak, str) and ak.isidentifier() and not keyword.iskeyword(ak):
                        parts.append(f"{id}.{ak} == ")
            parts.append(f"{repr(v)}")
            result.append("".join(parts))
        for k, v in vars(self).items():
            if k not in ("_aliases"):
                result.append(f"    {id}.{k} == {repr(v)}")
        return "\n".join(result)

    def __eq__(self, other):
        if isinstance(other, CleverDict):
            return self.items() == other.items() and vars(self) == vars(other)
        return NotImplemented


if __name__ == "__main__":
    pass
    
