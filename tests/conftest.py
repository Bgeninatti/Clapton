from .fixtures import (node, ser_answer_all, ser_raises_read_exception,
                      ser_raises_write_exception, virtual_node)


def pytest_addoption(parser):
    parser.addoption("--tklan",
                     action="store_true",
                     default=False,
                     dest='tklan',
                     help="Run test that needs a TKLan network. \n" +
                     " The test run with the node 14 of the TKLan, " +
                     "the one that coresponds with equipment TKL676.")


def pytest_configure(config):
    if not config.option.tklan:
        setattr(config.option, 'markexpr', 'not tklan')
