"""
Interfaces for specifications and related classes. 

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 2, 2011.
"""
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['IFilterSpecificationFactory',
           'IFilterSpecificationVisitor',
           'IOrderSpecificationFactory',
           'IOrderSpecificationVisitor',
           'ISpecification',
           ]


# begin interfaces pylint: disable=E0213,W0232,E0211

class ISpecification(Interface):
    """
    Specification interface.
    """

    operator = Attribute('The operator for this specification. Subclass of '
                         ':class:`everest.querying.operators.Operator`.')

    def accept(visitor):
        """
        Accept the given visitor into this specification.
        
        This triggers visits of this specification and all other dependent
        specifications which in turn dispatch appropriate visiting operations.

        :param visitor: a visitor that packages related operations
        :type visitor: object implementing :class:`ISpecificationVisitor`
        """


class IFilterSpecificationFactory(Interface):
    """
    Filter specification factory interface.
    """

    def create_equal_to(attr_name, attr_value):
        "Create an equal-to filter specification."

    def create_starts_with(attr_name, attr_value):
        "Create a starts-with filter specification."

    def create_ends_with(attr_name, attr_value):
        "Create an ends-with filter specification."

    def create_contains(attr_name, attr_value):
        "Create a contains filter specification."

    def create_contained(attr_name, attr_value):
        "Create a contained filter specification."

    def create_greater_than_or_equal_to(attr_name, attr_value):
        "Create a greater-than-or-equal-to filter specification."

    def create_greater_than(attr_name, attr_value):
        "Create a greater-than filter specification."

    def create_less_than_or_equal_to(attr_name, attr_value):
        "Create a less-than-or-equal-to filter specification."

    def create_less_than(attr_name, attr_value):
        "Create a less-than filter specification."

    def create_in_range(attr_name, from_value, to_value):
        "Create an in-range filter specification."
        raise NotImplementedError('Abstract method')

    def create_conjunction(left_spec, right_spec):
        "Create a conjunction of two filter specifications."

    def create_disjunction(left_spec, right_spec):
        "Create a disjunction of two filter specifications."

    def create_negation(wrapped):
        "Create a negation of a filter specification."


class IOrderSpecificationFactory(Interface):
    """
    Order specification factory interface.
    """

    def create_ascending(attr_name):
        "Create an ascending order specification."

    def create_descending(attr_name):
        "Create a descending order specification."



class ISpecificationVisitor(Interface):
    """
    Interface for specification visitors.
    
    The various visiting methods dispatch to the appropriate visiting 
    operations depending on the passed specification's operator.
    """

    expression = Attribute('The expression the visitor built.')

    def visit_nullary(spec):
        """
        Visits the given specification with a dispatched visiting operation.
        """

    def visit_unary(spec):
        """
        Visits the given specification, passing the expression obtained from
        processing the last specification as an argument to the visiting
        operation.
        """

    def visit_binary(spec):
        """
        Visits the given specification, passing the expressions obtained from
        processing the last two specifications as an arguments to the visiting
        operation.
        """


class IFilterSpecificationVisitor(ISpecificationVisitor):
    """
    Interface for filter specification visitors.
    """

    def _conjunction_op(spec, *expressions):
        """
        Visiting operation for conjunction specifications.
        """

    def _disjunction_op(spec, *expressions):
        """
        Visiting operation for disjunction specifications.
        """

    def _negation_op(spec, expression):
        """
        Visiting operation for negation specifications.
        """

    def _starts_with_op(spec):
        """
        Visiting operation for value starts with specifications.
        """

    def _ends_with_op(spec):
        """
        Visiting operation for value ends with specifications.
        """

    def _contains_op(spec):
        """
        Visiting operation for value contains specifications.
        """

    def _contained_op(spec):
        """
        Visiting operation for value contained specifications.
        """

    def _equal_to_op(spec):
        """
        Visiting operation for value equal to specifications.
        """

    def _less_than_op(spec):
        """
        Visiting operation for value less than specifications.
        """

    def _less_than_or_equal_to_op(spec):
        """
        Visiting operation for value less than or equal to specifications.
        """

    def _greater_than_op(spec):
        """
        Visiting operation for value greater than specifications.
        """

    def _greater_than_or_equal_to_op(spec):
        """
        Visiting operation for value greater than or equal to specifications.
        """

    def _in_range_op(spec):
        """
        Visiting operation for value in range specifications.
        """


class IOrderSpecificationVisitor(ISpecificationVisitor):
    """
    Interface for order specification visitors that generate a query 
    expression.
    """

    def _conjunction_op(spec, *expressions):
        """
        Visiting operation for conjunction specifications.
        """

    def _asc_op(attr_name):
        """
        Visiting operation for ascending order specifications.
        """

    def _desc_op(attr_name):
        """
        Visiting operation for descending order specifications.
        """

# end interfaces pylint: enable=E0213,W0232,E0211
