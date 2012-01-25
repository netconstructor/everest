"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Aggregate implementations.

Created on Sep 25, 2011.
"""

from everest.db import Session
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IAggregateImplementation
from everest.exceptions import DuplicateException
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['AggregateImpl',
           'MemoryAggregateImpl',
           'OrmAggregateImpl',
           ]


class AggregateImpl(object):
    """
    Abstract base class for all aggregate implementations.
    """
    implements(IAggregate, IAggregateImplementation)

    def __init__(self, entity_class):
        """
        Constructor:

        :param entity_class: the entity class (type) of the entities in this
            aggregate.
        :type entity_class: a class implementing
            :class:`everest.entities.interfaces.IEntity`
        """
        if self.__class__ is AggregateImpl:
            raise NotImplementedError('Abstract class.')
        #: Relationship of entities in this aggregate to a parent entity.
        self._relationship = None
        #: Entity class (type) of the entities in this aggregate.
        self.entity_class = entity_class
        #: Specification for filtering
        #: (:class:`everest.querying.specifications.FilterSpecification`).
        #: Attribute names in this specification are relative to the entity. 
        self._filter_spec = None
        #: Specification for ordering
        #: (:class:`everest.querying.specifications.OrderSpecification`).
        #: Attribute names in this specification are relative to the entity. 
        self._order_spec = None
        #: Key for slicing. (:type:`slice`).
        self._slice_key = None

    @classmethod
    def create(cls, entity_class):
        raise NotImplementedError('Abstract method.')

    def clone(self):
        clone = self.__class__.create(self.entity_class)
        clone._relationship = self._relationship
        clone._filter_spec = self._filter_spec
        clone._order_spec = self._order_spec
        clone._slice_key = self._slice_key
        return clone

    def count(self):
        raise NotImplementedError('Abstract method')

    def get_by_id(self, id_key):
        raise NotImplementedError('Abstract method')

    def get_by_slug(self, slug):
        raise NotImplementedError('Abstract method')

    def iterator(self):
        raise NotImplementedError('Abstract method')

    def add(self, entity):
        raise NotImplementedError('Abstract method')

    def remove(self, entity):
        raise NotImplementedError('Abstract method')

    def set_relationship(self, relationship):
        self._relationship = relationship

    def _get_filter(self):
        return self._filter_spec

    def _set_filter(self, filter_spec):
        self._filter_spec = filter_spec
        self._apply_filter()

    filter = property(_get_filter, _set_filter)

    def _get_order(self):
        return self._order_spec

    def _set_order(self, order_spec):
        self._order_spec = order_spec
        self._apply_order()

    order = property(_get_order, _set_order)

    def _get_slice(self):
        return self._slice_key

    def _set_slice(self, slice_key):
        self._slice_key = slice_key
        self._apply_slice()

    slice = property(_get_slice, _set_slice)

    def _apply_filter(self):
        """
        Called when the filter specification has changed.
        """
        raise NotImplementedError('Abstract method')

    def _apply_order(self):
        """
        Called when the order specification has changed.
        """
        raise NotImplementedError('Abstract method')

    def _apply_slice(self):
        """
        Called when the slice key has changed.
        """
        raise NotImplementedError('Abstract method')


class MemoryAggregateImpl(AggregateImpl):
    """
    In-memory implementation for aggregates.

    :note: Filtering and ordering in memory aggregates is very slow. Also,
        when "blank" entities without an ID and a slug are added to a
        memory aggregate, they can not be retrieved using the
        :method:`get_by_id` or :method:`get_by_slug` methods since there 
        is no mechanism to autogenerate IDs or slugs.
    """
    def __init__(self, entity_class):
        AggregateImpl.__init__(self, entity_class)
        #
        self.__entities = []

    @classmethod
    def create(cls, entity_class):
        return cls(entity_class)

    def clone(self):
        clone = super(MemoryAggregateImpl, self).clone()
        if self._relationship is None:
            clone.__entities = self.__entities
        return clone

    def count(self):
        return len(list(self.iterator()))

    def get_by_id(self, id_key):
        ents = self._get_entities()
        matching_ents = self.__filter_by_attr(ents, 'id', id_key)
        if len(matching_ents) == 1:
            ent = matching_ents[0]
        elif len(matching_ents) == 0:
            ent = None
        else:
            raise DuplicateException('Duplicates found for ID "%s".' % id_key)
        return ent

    def get_by_slug(self, slug):
        ents = self._get_entities()
        matching_ents = self.__filter_by_attr(ents, 'slug', slug)
        if len(matching_ents) == 1:
            ent = matching_ents[0]
        elif len(matching_ents) == 0:
            ent = None
        else:
            raise DuplicateException('Duplicates found for slug "%s".' % slug)
        return ent

    def iterator(self):
        ents = self._get_entities()
        if not self._filter_spec is None:
            visitor = get_utility(IFilterSpecificationVisitor,
                                  name=EXPRESSION_KINDS.EVAL)()
            self._filter_spec.accept(visitor)
            ents = visitor.expression(ents)
        if not self._order_spec is None:
            visitor = get_utility(IOrderSpecificationVisitor,
                                  name=EXPRESSION_KINDS.EVAL)()
            self._order_spec.accept(visitor)
            ents = visitor.expression(ents)
        if not self._slice_key is None:
            ents = ents[self._slice_key]
        for ent in ents:
            yield ent

    def add(self, entity):
        if not isinstance(entity, self.entity_class):
            raise ValueError('Can only add entities of type "%s" to this '
                             'aggregate.' % self.entity_class)
        if not hasattr(entity, 'id'):
            raise ValueError('Entities added to a memory aggregrate have to '
                             'have an ID (`id` attribute).')
        if not hasattr(entity, 'slug'):
            raise ValueError('Entities added to a memory aggregrate have to '
                             'have a slug (`slug` attribute).')
        entity_id = entity.id
        entity_slug = entity.slug
        if not entity_id is None:
            if entity_slug is None:
                raise ValueError('Entities added to a memory aggregate which '
                                 'specify an ID also need to specify a slug.')
            elif self.__check_existing(entity):
                raise ValueError('Entity with ID "%s" or slug "%s" is already '
                                 'present.' % (entity_id, entity_slug))
        ents = self._get_entities()
        ents.append(entity)

    def remove(self, entity):
        ents = self._get_entities()
        ents.remove(entity)

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def _get_entities(self):
        """
        Returns the entities held by this memory aggregate.
        
        :returns:  list of objects implementing 
            :class:`everest.entities.interfaces.IEntity`
        """
        if self._relationship is None:
            ents = self.__entities
        else:
            ents = self._relationship.children
        return ents

    def _set_entities(self, entities):
        """
        Sets the entities held by this memory aggregate.
        
        :param entities: list of objects implementing 
            :class:`everest.entities.interfaces.IEntity`
        """
        if self._relationship is None:
            self.__entities = entities
        else:
            self._relationship.children = entities

    def __check_existing(self, entity):
        ents = self._get_entities()
        found = [ent for ent in ents
               if ent.id == entity.id or ent.slug == entity.slug]
        return len(found) > 0

    def __filter_by_attr(self, ents, attr, value):
        if self._filter_spec is None:
            filtered_ents = \
                [ent for ent in ents if getattr(ent, attr) == value]
        else:
            filtered_ents = \
                [ent for ent in ents if getattr(ent, attr) == value
                 if self._filter_spec.is_satisfied_by(ent)]
        return filtered_ents


class OrmAggregateImpl(AggregateImpl):
    """
    ORM implementation for aggregates.
    """
    def __init__(self, entity_class, session, search_mode=False):
        AggregateImpl.__init__(self, entity_class)
        self._session = session
        self._search_mode = search_mode

    @classmethod
    def create(cls, entity_class):
        session = Session()
        return cls(entity_class, session)

    def count(self):
        if not self._relationship is None:
            # We need a flush here because we may have newly added entities
            # in the aggregate which need to get an ID *before* we build the
            # relation filter spec.
            self._session.flush()
        if self.__defaults_empty:
            cnt = 0
        else:
            cnt = self.__get_filtered_query(None).count()
        return cnt

    def get_by_id(self, id_key):
        query = self.__get_filtered_query(id_key)
        try:
            ent = query.filter_by(id=id_key).one()
        except NoResultFound:
            ent = None
        except MultipleResultsFound:
            raise DuplicateException('Duplicates found for ID "%s".' % id_key)
        return ent

    def get_by_slug(self, slug):
        query = self.__get_filtered_query(slug)
        try:
            ent = query.filter_by(slug=slug).one()
        except NoResultFound:
            ent = None
        except MultipleResultsFound:
            raise DuplicateException('Duplicates found for slug "%s".' % slug)
        return ent

    def iterator(self):
        if not self._relationship is None:
            # We need a flush here because we may have newly added entities
            # in the aggregate which need to get an ID *before* we build the
            # relation filter spec.
            self._session.flush()
        if self.__defaults_empty:
            yield
        else:
            # We need a flush here because we may have newly added entities
            # in the aggregate which need to get an ID *before* we build the
            # query expression.
            self._session.flush()
            query = self._get_data_query()
            for obj in iter(query):
                yield obj

    def add(self, entity):
        if self._relationship is None:
            self._session.add(entity)
            self._session.flush()
        else:
            self._relationship.children.append(entity)

    def remove(self, entity):
        if self._relationship is None:
            self._session.delete(entity)
        else:
            self._relationship.children.remove(entity)

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def _query_generator(self, query, key): # unused pylint: disable=W0613
        return query

    def _filter_visitor_factory(self):
        visitor_cls = get_utility(IFilterSpecificationVisitor,
                                  name=EXPRESSION_KINDS.SQL)
        return visitor_cls(self.entity_class)

    def _order_visitor_factory(self):
        visitor_cls = get_utility(IOrderSpecificationVisitor,
                                  name=EXPRESSION_KINDS.SQL)
        return visitor_cls(self.entity_class)

    def _get_base_query(self):
        if self._relationship is None:
            query = self._session.query(self.entity_class)
        else:
            # Pre-filter the base query with the relation specification.
            rel_spec = self._relationship.specification
            visitor = self._filter_visitor_factory()
            rel_spec.accept(visitor)
            expr = visitor.expression
            query = self._session.query(self.entity_class).filter(expr)
        return query

    def _get_data_query(self):
        query = self.__get_ordered_query(self._slice_key)
        if not self._slice_key is None:
            query = query.slice(self._slice_key.start,
                                self._slice_key.stop)
        return query

    def __get_filtered_query(self, key):
        query = self._query_generator(self._get_base_query(), key)
        if not self._filter_spec is None:
            visitor = self._filter_visitor_factory()
            self._filter_spec.accept(visitor)
            query = query.filter(visitor.expression)
        return query

    def __get_ordered_query(self, key):
        query = self.__get_filtered_query(key)
        if not self._order_spec is None:
            visitor = self._order_visitor_factory()
            self._order_spec.accept(visitor)
            for join_expr in visitor.get_joins():
                # FIXME: only join when needed here # pylint:disable=W0511
                query = query.outerjoin(join_expr)
            query = query.order_by(*visitor.expression)
        return query

    @property
    def __defaults_empty(self):
        return self._filter_spec is None and self._search_mode
