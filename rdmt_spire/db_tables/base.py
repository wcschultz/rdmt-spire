"""Defines base class for all SQL tables.

This module contains the basic DeclarativeBase class to be used by all other 
table_def files for table creation.

Copied from rtbdb code.

"""
import datetime
import inspect
import logging

from sqlalchemy import Boolean, DateTime, Float, Integer, String, event
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base table class for using SQLAlchemy for database interfacing.
    
    All class functions should begin with '_'.
    
    """

    def _as_dict(self) -> dict:
        """Represent class as dictionary."""
        d = self.__dict__.copy()
        if "_sa_instance_state" in d.keys():
            del [d["_sa_instance_state"]]
        return d

    def __eq__(self, other):
        """Allow for == boolean testing."""
        return self._as_dict() == other._as_dict()

    def __repr__(self, level=1, max_level=2, original_class_name=None) -> str:
        """Produce pretty print statements without recursion."""
        d = self._as_dict()
        rstr = f"{self.__class__.__name__}("
        for k, v in d.items():
            if isinstance(v, list) and isinstance(v[0], Base):
                rstr += f"{k}=[list of {len(v)} {v[0].__class__.__name__}], "
            elif isinstance(v, Base):
                if original_class_name == v.__class__.__name__:
                    continue
                if level < max_level:
                    rstr += f"{k}={v.__repr__(level=level+1, original_class_name=self.__class__.__name__)}, "
            else:
                rstr += f"{k}={v}, "
        if rstr[-1] == " ":
            rstr = rstr[:-2]
        return rstr + ")"

    def _get_columns(self) -> list:
        """Gather all useful columns from table.
        
        Returns
        -------
        list of strings:
            attributes of the class without a '_' prefix which are 
        the columns of the table by definition.

        """
        attrs = dir(self)
        if 'registry' in attrs:
            attrs.remove('registry')
        if 'metadata' in attrs:
            attrs.remove('metadata')
        cols = []
        for a in attrs:
            if (a[0] != "_") and (not inspect.ismethod(getattr(self, a))):
                cols.append(a)
        return cols

    def _get_verification_columns(self) -> list:
        """List which columns to verify if two classes are equal using _verify().
        
        This function is a placeholder. 
        It needs to be updated in each subclass. 

        Returns
        -------
        list of strings:
            contains the column names that should be verified in each table
            
        """
        raise NotImplementedError

    def _verify(self, other, retry_write: bool = True, 
                return_result: bool = False):
        """Ensure two table classes are equal.

        Parameters
        ----------
        other: table class
            Another instance of the same table class as self
        retry_write: boolean (default=True)
            If True, function attempts to reset the attribute in self with the 
            value from other.
        return_result: boolean (default=False)
            If True, returns the boolean 'verify_result' that contains the 
            result of the verification.

        Returns
        -------
        verify_result: boolean
            True if the two table classes match, False if they do not.

        """
        verify_result = True
        # ensure self is the same class as other (not right yet...)
        if type(self).__name__ != type(other).__name__:
            verify_result = False
            raise ValueError(
                f"_verify attempted to compare {type(self).__name__} \
                    with {type(other).__name__}"
            )

        # ensure list_of_column method was implemented
        verification_columns = self._get_verification_columns()
        assert all(isinstance(vc, str) for vc in verification_columns), \
            f"All verification column names must be strings. Check \
                _get_verification_columns() in {type(self).__name__}"

        # loop over columns and check if values are equal
        for attr in verification_columns:
            if getattr(self, attr) != getattr(other, attr):
                verify_result = False
                logging.error(
                    f"Mismatch for {type(self).__name__}.{attr}: \
                        {getattr(self, attr)} in self, {getattr(other, attr)} \
                        in other."
                )
                if retry_write:
                    logging.warning("Attempting to fix mismatch by rewriting.")
                    setattr(self, attr, getattr(other, attr))

        if return_result:
            if retry_write:
                verify_result = self._verify(other, retry_write=False, return_result=True)
            return verify_result


# Code below here allows for the datatypes of class attributes
# to be validated upon adding them to sub-classes


# Set up datatype validators
def validate_int(class_, key, value):
    """Catch non-integer setting of integer attribute."""
    if not isinstance(value, int):
        try:
            value = int(value)
        except Exception:
            logging.error(f"Failed to convert {class_.__name__}.{key} to int")
            raise TypeError(f"{class_.__name__}.{key} must be int")
    return value


def validate_float(class_, key, value):
    """Catch non-float setting of float attribute."""
    if not isinstance(value, float):
        try:
            value = float(value)
        except Exception:
            logging.error(
                f"Failed to convert {class_.__name__}.{key} to float"
            )
            raise TypeError(f"{class_.__name__}.{key} must be float")
    return value


def validate_string(class_, key, value):
    """Catch non-string setting of string attribute."""
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            logging.error(f"Failed to convert {class_.__name__}.{key} to str")
            raise TypeError(f"{class_.__name__}.{key} must be str")
    return value


def validate_bool(class_, key, value):
    """Catch non-boolean setting of boolean attribute."""
    if not isinstance(value, bool):
        try:
            value = bool(value)
        except Exception:
            logging.error(f"Failed to convert {class_.__name__}.{key} to bool")
            raise TypeError(f"{class_.__name__}.{key} must be bool")
    return value


def validate_datetime(class_, key, value):
    """Catch non-datetime setting of datetime attribute."""
    if not isinstance(value, datetime.datetime):
        logging.error(
            f"Invalid datatype for {class_.__name__}.{key}. Expected \
                datetime.datetime but received ({value}) as \
                {type(value).__name__}"
        )
        raise TypeError(
            f"Invalid datatype for {class_.__name__}.{key}. \
                Must be datetime.datetime."
        )
    # TODO: this should be deprecated. Removing for now to see if it breaks things.
    #elif value.microsecond > 0:
    #    raise ValueError(
    #        "Please set datetime.microsecond to 0 as it produces comparison \
    #           errors when uploaded to the database. This can simply be done \
    #            using datetime.today().replace(microsecond=0) to get the \
    #            current time."
    #    )
    return value


validators = {
    Integer: validate_int,
    Float: validate_float,
    String: validate_string,
    Boolean: validate_bool,
    DateTime: validate_datetime,
}


# trigger event when a table class attribute is instrumented
@event.listens_for(Base, "attribute_instrument")
def configure_listener(class_, key, inst):
    """Listen for attribute setting."""
    if not hasattr(inst.property, "columns"):
        return

    # trigger when instrumented attribute is set
    @event.listens_for(inst, "set", retval=True)
    def set_(instance, value, oldvalue, initiator):
        validator = validators.get(inst.property.columns[0].type.__class__)
        if validator:
            return validator(class_, key, value)
        else:
            return value
