# -*- coding: utf8 -*-

# Copyright 2008 Jaap Karssenberg <pardus@cpan.org>

'''
This package contains the main Notebook class together
with basic classed like Page and Namespace.

This package defines the public interface towards the
noetbook.  As a backend it uses one of more packages from
the 'stores' namespace.
'''

import weakref

from zim.fs import *
import zim.stores

def get_notebook(notebook):
	'''Takes a path or name and returns a notebook object'''
	# TODO check notebook list if notebook is not a path
	if not isinstance(notebook, Dir): notebook = Dir(notebook)
	if notebook.exists():
		return Notebook(path=notebook)
	else:
		raise Exception, 'no such notebook: %s' % notebook


class LookupError(Exception):
	pass


class Notebook(object):
	'''FIXME'''

	def __init__(self, path=None, config=None):
		'''FIXME'''
		self.namespaces = []
		self.stores = {}
		self.page_cache = weakref.WeakValueDictionary()

		if isinstance(path, Dir):
			self.dir = path
			if config is None:
				pass # TODO: load config file from dir
			# TODO check if config defined root namespace
			self.add_store('', 'files') # set root
			# TODO add other namespaces from config
		elif isinstance(path, File):
			assert False, 'TODO: support for single file notebooks'
		elif not path is None:
			assert False, 'path should be either File or Dir'

	def add_store(self, namespace, store, **args):
		'''Add a store to the notebook under a specific namespace.
		All other args will be passed to the store.
		Returns the store object.
		'''
		mod = zim.stores.get_store(store)
		mystore = mod.Store(
			notebook=self,
			namespace=namespace,
			**args
		)
		self.stores[namespace] = mystore
		self.namespaces.append(namespace)

		# keep order correct for lookup
		self.namespaces.sort()
		self.namespaces.reverse()

		return mystore

	def get_store(self, name, resolve=False):
		'''Returns the store object to handle a page or namespace.'''
		if resolve:
			# check case insensitive
			lname = name.lower()
			for namespace in self.namespaces:
				# longest match first because of reverse sorting
				if lname.startswith( namespace.lower() ):
					return self.stores[namespace]
		else:
			for namespace in self.namespaces:
				# longest match first because of reverse sorting
				if name.startswith(namespace):
					return self.stores[namespace]
		raise LookupError, 'Could not find store for: %s' % name

	def get_stores(self, name):
		'''Returns a list of (path, store) for all stores in
		the path to a secific page. The 'path' item in the result is
		the maximum part of the ath handled by that store.
		'''
		stores = []
		path = name
		for namespace in self.namespaces:
			# longest match first because of reverse sorting
			if name.startswith(namespace):
				store = self.stores[namespace]
				stores.append( (path, store) )
				# set path for next match to namespace part
				# which is not covered by this store
				i = store.namespace.rfind(':')
				path = store.namespace[:i]
		return stores

	def normalize_name(self, name):
		'''Normalizes a page name to a valid form.
		Raises a LookupError if name is empty.
		'''
		name = name.strip(':')
		if not name:
			raise LookupError, 'Empty page name'
		parts = [p for p in name.split(':') if p]
		return ':'+':'.join(parts)


	# Public interface

	def resolve_name(self, name, namespace=''):
		'''Returns a proper page name from links or user input.

		'namespace' is the namespace of the refering page, if any.

		If namespace is empty or if the page name starts with a ':'
		the name is considered an absolute name and only case is
		resolved. If the page does not exist the last part(s) of the
		name will remain in the case as given.

		If the name is relative to namespace we first look for a match
		of the first part of the name in the path. If that fails we
		do a search for the first part of the name through all
		namespaces in the path. If no match was found we default to
		the name relative to 'namespace'.
		'''
		isabs = name.startswith(':') or not namespace
		name = self.normalize_name(name)

		# If I'm not mistaken each call to this method will
		# result in exactly one call to the corresponding method
		# for a specific store (but potentially for multiple stores).

		def resolve_abs(name):
			# only resolve case for absolute name
			# keep case as is when not found
			store = self.get_store(name, resolve=True)
			n = store.resolve_name(name)
			return n or name

		if isabs:
			return resolve_abs(name)
		else:
			# first check if we see an explicit match in the path
			anchor = name.split(':')[1].lower()
			path = reversed( namespace.lower().split(':')[1:] )
			if anchor in path:
				# ok, so we can shortcut to an absolute path
				i = path.index(anchor) + 1
				path = reversed(path[i:])
				path.append( name.lstrip(':') )
				name = ':'.join(path)
				return resolve_abs(name)
			else:
				# no luck, do a search through the whole path
				stores = self.get_stores(namespace)
				for path, store in stores:
					n = store.resolve_name(name, namespace=path)
					if not n is None: return n
				# name not found, keep case as is
				return namespace+':'+name

	def get_page(self, name):
		'''Returns a Page object'''
		name = self.normalize_name(name)
		if name in self.page_cache:
			return self.page_cache[name]
		else:
			store = self.get_store(name)
			page = store.get_page(name)
			self.page_cache[name] = page
			return page

	def get_root(self):
		'''Returns a Namespace object for root namespace.'''
		return self.stores[''].get_root()

	def get_namespace(self, namespace):
		'''Returns a Namespace object for 'namespace'.'''
		namespace = self.normalize_name(namespace)
		store = self.get_store(namespace)
		return store.get_namespace(namesace)

	#~ def move_page(self, name, newname):
		#~ '''FIXME'''

	#~ def copy_page(self, name, newname):
		#~ '''FIXME'''

	#~ def del_page(self, name):
		#~ '''FIXME'''

	#~ def search(self):
		#~ '''FIXME'''
		#~ pass # TODO search code


class Page(object):
	'''FIXME'''

	def __init__(self, name, store, source=None, format=None):
		'''Construct Page object.
		Needs at least a name and a store object.
		The source object and format module are optional but go together.
		'''
		#assert name is valid
		assert not (source and format is None) # these should come as a pair
		self.name     = name
		self.store    = store
		self.children = None
		self.source   = source
		self.format   = format
		self._tree    = None


	def get_basename(self):
		i = self.name.rfind(':') + 1
		return self.name[i:]

	def raise_set(self):
		# TODO raise ro property
		pass

	basename = property(get_basename, raise_set)

	def isempty(self):
		'''Returns True if this page has no content'''
		if self.source:
			return not self.source.exists()
		else:
			return not self._tree

	def get_parse_tree(self):
		'''Returns contents as a parse tree or None'''
		if self.source:
			if self.isempty():
				return None
			parser = self.format.Parser()
			file = self.source.open()
			tree = parser.parse(file)
			file.close()
			return tree
		else:
			return self._tree

	def set_parse_tree(self, tree):
		'''Save a parse tree to page source'''
		if self.source:
			dumper = self.format.Dumper()
			file = self.source.open('w')
			dumper.dump(tree, file)
			file.close()
		else:
			self._tree = tree

	def get_text(self, format='wiki'):
		'''Returns contents as string'''
		tree = self.get_parse_tree()
		if tree:
			import zim.formats
			dumper = zim.formats.get_format(format).Dumper()
			return dumper.dump_string(tree)
		else:
			return ''

	def path(self):
		'''Generator function for parent names
		can be used for:

			for namespace in page.path():
				if namespace.page('foo').exists:
					# ...
		'''
		path = self.name.split(':')
		path.pop(-1)
		while len(path) > 0:
			namespace = path.join(':')
			yield Namespace(namespace, self.store)


class Namespace(object):
	'''Iterable object for namespaces'''

	def __init__(self, namespace, store):
		'''Constructor needs a namespace and a store object'''
		self.name = namespace
		self.store = store

	def __iter__(self):
		'''Calls the store.listpages generator function'''
		return self.store.list_pages( self.name )

	def walk(self):
		'''Generator to walk page tree recursively'''
		for page in self:
			yield page
			if page.children:
				for page in page.children.walk(): # recurs
					yield page
