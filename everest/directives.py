"""
ZCML directives for everest.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 16, 2011.
"""
from everest.configuration import Configurator
from everest.repository import REPOSITORIES
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from pyramid.threadlocal import get_current_registry
from pyramid_zcml import IViewDirective
from zope.configuration.config import GroupingContextDecorator # pylint: disable=E0611,F0401
from zope.configuration.config import IConfigurationContext # pylint: disable=E0611,F0401
from zope.configuration.fields import Bool # pylint: disable=E0611,F0401
from zope.configuration.fields import GlobalObject # pylint: disable=E0611,F0401
from zope.configuration.fields import Path # pylint: disable=E0611,F0401
from zope.configuration.fields import Tokens # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.schema import Choice # pylint: disable=E0611,F0401
from zope.schema import TextLine # pylint: disable=E0611,F0401
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION

__docformat__ = 'reStructuredText en'
__all__ = ['RESOURCE_KINDS',
           'RepresenterDirective',
           'ResourceDirective',
           'ResourceRepresenterAttributeDirective',
           'ResourceRepresenterDirective',
           'collection_view',
           'filesystem_repository',
           'member_view',
           'memory_repository',
           'messaging',
           'option',
           'orm_repository',
           'resource_view',
           ]


# interfaces to not have an __init__ # pylint: disable=W0232

class IRepositoryDirective(Interface):
    name = \
        TextLine(title=u"Name of this repository. Must be unique among all "
                        "repositories. If no name is given, or the name is "
                        "specified as 'DEFAULT', the built-in repository is "
                        "configured with the given directive.",
                 required=False
                 )
    aggregate_class = \
        GlobalObject(title=u"A class to use as the default aggregate "
                            "implementation for this repository.",
                     required=False)
    entity_store_class = \
        GlobalObject(title=u"A class to use as the entity store "
                            "implementation for this repository.",
                     required=False)
    make_default = \
        Bool(title=u"Indicates if this repository should be made the default "
                    "for all resources that do not explicitly specify a "
                    "repository. Defaults to False.",
             required=False
             )


def _repository(_context, name, make_default, agg_cls, ent_store_cls,
                repo_type, config_method, cnf):
    # Repository directives are applied eagerly. Note that custom repositories 
    # must be declared *before* they can be referenced in resource directives.
    discriminator = (repo_type, name)
    _context.action(discriminator=discriminator)
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    method = getattr(config, config_method)
    if name is None: # re-configure builtin repository.
        name = repo_type
    method(name, aggregate_class=agg_cls, entity_store_class=ent_store_cls,
           configuration=cnf, make_default=make_default)


class IMemoryRepositoryDirective(IRepositoryDirective):
    pass


def memory_repository(_context, name=None, make_default=False,
                      aggregate_class=None, entity_store_class=None):
    _repository(_context, name, make_default,
                aggregate_class, entity_store_class,
                REPOSITORIES.MEMORY, 'add_memory_repository', {})


class IFileSystemRepositoryDirective(IRepositoryDirective):
    directory = \
        Path(title=u"The directory the representation files for the "
                    "root collection resources are kept. Defaults to "
                    "the current working directory.",
             required=False,
             )
    content_type = \
        GlobalObject(title=u"The (MIME) content type to use for the "
                            "representation files. Defaults to CSV.",
                     required=False)


def filesystem_repository(_context, name=None, make_default=False,
                          aggregate_class=None, entity_store_class=None,
                          directory=None, content_type=None):
    """
    Directive for registering a file-system based repository.
    """
    cnf = {}
    if not directory is None:
        cnf['directory'] = directory
    if not content_type is None:
        cnf['content_type'] = content_type
    _repository(_context, name, make_default,
                aggregate_class, entity_store_class,
                REPOSITORIES.FILE_SYSTEM, 'add_filesystem_repository', cnf)


class IOrmRepositoryDirective(IRepositoryDirective):
    db_string = \
        TextLine(title=u"String to use to connect to the DB server. Defaults "
                        "to an in-memory sqlite DB.",
                 required=False)
    metadata_factory = \
        GlobalObject(title=u"Callback that initializes and returns the "
                            "metadata for the ORM.",
                     required=False)


def orm_repository(_context, name=None, make_default=False,
                   aggregate_class=None, entity_store_class=None,
                   db_string=None, metadata_factory=None):
    """
    Directive for registering an ORM based repository.
    """
    cnf = {}
    if not db_string is None:
        cnf['db_string'] = db_string
    if not metadata_factory is None:
        cnf['metadata_factory'] = metadata_factory
    _repository(_context, name, make_default,
                aggregate_class, entity_store_class,
                REPOSITORIES.ORM, 'add_orm_repository', cnf)


class IMessagingDirective(Interface):
    repository = \
        TextLine(title=u"Repository to use for the messaging system.",
                 required=True,
                 )
    reset_on_start = \
        Bool(title=u"Erase all stored user messages on startup. This only "
                    "has an effect in persistent repositories.",
             required=False)


def messaging(_context, repository, reset_on_start=False):
    """
    Directive for setting up the user message resource in the appropriate
    repository.
    
    :param str repository: The repository to create the user messages resource
      in.
    """
    discriminator = ('messaging', repository)
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    _context.action(discriminator=discriminator, # pylint: disable=E1101
                    callable=config.setup_messaging,
                    args=(repository,),
                    kw=dict(reset_on_start=reset_on_start))


class IResourceDirective(Interface):
    interface = \
        GlobalObject(title=u"The marker interface to use for this resource.",
                     required=True,
                     )
    member = \
        GlobalObject(title=u"The member resource class for this resource.",
                     required=True,
                     )
    entity = \
        GlobalObject(title=u"The entity class associated with the member "
                            "resource.",
                     required=True,
                     )
    collection = \
        GlobalObject(title=u"The collection resource class for the member "
                            "resource. If this is not specified, a dynamic "
                            "default class is created using the values of "
                            "`collection_root_name` and `collection_title` "
                            "as root name and title, respectively.",
                     required=False,
                     )
    collection_root_name = \
        TextLine(title=u"The name for the root collection (used as URL path "
                        "to the root collection inside the service). Defaults "
                        "to the root_name attribute of the collection class.",
                 required=False,
                 )
    collection_title = \
        TextLine(title=u"The name for the root collection (used as URL path "
                        "to the root collection inside the service). Defaults "
                        "to the root_name attribute of the collection class.",
                 required=False,
                 )
    repository = \
        TextLine(title=u"The name of the repository that should be used for "
                        "this resource. Defaults to 'MEMORY', the built-in "
                        "in-memory repository (i.e., no persistence); see "
                        "the IRepositoryDirective for other possible values.",
                 required=False)
    expose = \
        Bool(title=u"Flag indicating if this collection should be exposed in "
                    "the service.",
             default=True,
             required=False,
             )


class ResourceDirective(GroupingContextDecorator):
    """
    Directive for registering a resource. Calls
    :meth:`everest.configuration.Configurator.add_resource`.
    """
    implements(IConfigurationContext, IResourceDirective)

    def __init__(self, context, interface, member, entity,
                 collection=None, collection_root_name=None,
                 collection_title=None, repository=None, expose=True):
        self.context = context
        self.interface = interface
        self.member = member
        self.entity = entity
        self.collection = collection
        self.collection_root_name = collection_root_name
        self.collection_title = collection_title
        self.repository = repository
        self.expose = expose
        self.representers = {}

    def after(self):
        # Register resources eagerly so the various adapters and utilities are
        # available for other directives.
        discriminator = ('resource', self.interface)
        reg = get_current_registry()
        config = Configurator(reg, package=self.context.package)
        config.add_resource(self.interface, self.member, self.entity,
                            collection=self.collection,
                            collection_root_name=self.collection_root_name,
                            collection_title=self.collection_title,
                            repository=self.repository,
                            expose=self.expose,
                            _info=self.context.info)
        for key, value in self.representers.iteritems():
            cnt_type, rc_kind = key
            opts, mp_opts = value
            if rc_kind == RESOURCE_KINDS.member:
                rc = get_member_class(self.interface)
            elif rc_kind == RESOURCE_KINDS.collection:
                rc = get_collection_class(self.interface)
            else: # None
                rc = self.interface
            discriminator = ('resource_representer', rc, cnt_type, rc_kind)
            self.action(discriminator=discriminator, # pylint: disable=E1101
                        callable=config.add_resource_representer,
                        args=(rc, cnt_type),
                        kw=dict(options=opts,
                                attribute_options=mp_opts,
                                _info=self.context.info),
                        )


def _resource_view(_context, for_, default_content_type,
                   config_callable_name, kw):
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    config_callable = getattr(config, config_callable_name)
    option_tuples = tuple(sorted([(k, str(v)) for (k, v) in kw.items()]))
    kw['default_content_type'] = default_content_type
    for rc in for_:
        discriminator = ('resource_view', rc, config_callable_name) \
                        + option_tuples
        _context.action(discriminator=discriminator, # pylint: disable=E1101
                        callable=config_callable,
                        args=(rc,),
                        kw=kw)


class IResourceViewDirective(IViewDirective):
    for_ = \
        Tokens(title=u"The resource classes or interfaces to set up views "
                      "for. For each interface in the sequence, views for "
                      "the associated member resource class (member_view), "
                      "the associated collection resource class "
                      "(collection_view) or both (resource_view) are"
                      "generated.",
               required=True,
               value_type=GlobalObject())
    default_content_type = \
        GlobalObject(title=u"The default MIME content type to use when the "
                            "client does not indicate a preference.",
                     required=False)
    request_method = \
        Tokens(title=u"One or more request methods that need to be matched.",
               required=True,
               value_type=Choice(values=('GET', 'POST', 'PUT', 'DELETE',
                                         'FAKE_DELETE', 'FAKE_PUT'),
                                 default='GET',
                                 ),
               )


def resource_view(_context, for_, default_context_type=None, **kw):
    _resource_view(_context, for_, default_context_type,
                   'add_resource_view', kw)


def collection_view(_context, for_, default_context_type=None, **kw):
    _resource_view(_context, for_, default_context_type,
                   'add_collection_view', kw)


def member_view(_context, for_, default_context_type=None, **kw):
    _resource_view(_context, for_, default_context_type,
                   'add_member_view', kw)


class IRepresenterDirective(Interface):
    content_type = \
        GlobalObject(title=u"The (MIME) content type for the representer "
                            "to configure. If this is given, the "
                            "'representer_class' option must not be given.",
                     required=False)
    representer_class = \
        GlobalObject(title=u"Class to use for the representer.  If this is "
                            "given, the 'content_type' option must not be "
                            "given.",
                     required=False)


class RepresenterDirective(GroupingContextDecorator):

    implements(IConfigurationContext, IRepresenterDirective)

    def __init__(self, context, content_type=None, representer_class=None):
        self.context = context
        self.content_type = content_type
        self.representer_class = representer_class
        self.options = {}

    def after(self):
        discriminator = \
            ('representer',
             self.content_type or self.representer_class.content_type)
        self.action(discriminator=discriminator) # pylint: disable=E1101
        # Representers are created eagerly so the resource declarations can use
        # them.
        reg = get_current_registry()
        config = Configurator(reg, package=self.context.package)
        config.add_representer(content_type=self.content_type,
                               representer_class=self.representer_class,
                               options=self.options)


class RESOURCE_KINDS(object):
    member = 'member'
    collection = 'collection'


class IResourceRepresenterDirective(Interface):
    content_type = \
        GlobalObject(title=u"The (MIME) content type the representer manages.",
                     required=True)
    kind = \
        Choice(values=(RESOURCE_KINDS.member, RESOURCE_KINDS.collection),
               title=u"Specifies the kind of resource the representer should "
                      "be used for ('member' or 'collection'). If this is "
                      "not provided, the representer is used for both "
                      "resource kinds.",
               required=False)


class ResourceRepresenterDirective(GroupingContextDecorator):
    """
    Grouping directive for registering a representer for a given resource(s) 
    and content type combination. Delegates the work to a
    :class:`everest.configuration.Configurator`.
    """
    implements(IConfigurationContext, IResourceRepresenterDirective)

    def __init__(self, context, content_type, kind=None):
        self.context = context
        self.content_type = content_type
        self.kind = kind
        self.options = {}
        self.attribute_options = {}

    def after(self):
        attribute_options = None if len(self.attribute_options) == 0 \
                            else self.attribute_options
        options = self.options
        self.context.representers[(self.content_type, self.kind)] = \
                                                (options, attribute_options)


class IResourceRepresenterAttributeDirective(Interface):
    name = \
        TextLine(title=u"Name of the representer attribute.")


class ResourceRepresenterAttributeDirective(GroupingContextDecorator):
    implements(IConfigurationContext, IResourceRepresenterAttributeDirective)

    def __init__(self, context, name):
        self.context = context
        self.name = name
        self.options = {}

    def after(self):
        # Convert the (nested) attribute names into keys.
        key = tuple(self.name.split('.'))
        self.context.attribute_options[key] = self.options


class IOptionDirective(Interface):
    name = \
        TextLine(title=u"Name of the option.")
    value = \
        TextLine(title=u"Value of the option.")
    type = \
        GlobalObject(title=u"Type of the option. This is only needed if the "
                            "option value needs to be something else than a "
                            "string; should be a Zope configuration field "
                            "type such as zope.configuration.fields.Bool.",
                     required=False)


def option(_context, name, value, type=None): # pylint: disable=W0622
    grouping_context = _context.context
    if not type is None:
        field = type()
        value = field.fromUnicode(value)
    elif name in (IGNORE_OPTION, IGNORE_ON_READ_OPTION,
                  IGNORE_ON_WRITE_OPTION, WRITE_AS_LINK_OPTION):
        field = Bool()
        value = field.fromUnicode(value)
    grouping_context.options[name] = value

# pylint: enable=W0232
