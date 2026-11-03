"""Order checks (hard rule H6): every order we produce passes the competition's own checks."""
from vn2_simulate import check_order


def validate(orders, index, name="The order"):
    """Return the orders as whole numbers indexed like the template, or raise OrderError.

    `check_order` is the official check: 599 rows in the template order, whole numbers, 0 or
    more. Using it (rather than our own copy) means our orders can never break the rules.
    """
    return check_order(orders, index, name)
