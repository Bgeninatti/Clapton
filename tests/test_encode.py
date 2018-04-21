import pytest
from ClaptonBase import encode
from ClaptonBase.exceptions import EncodeError


@pytest.mark.parametrize("sender,destination,expected", [
    (15, 15, b'\xff'),
    (7, 14, b'\x7e'),
    (9, 2, b'\x92'),
])
def test_sender_destination_ok(sender, destination, expected):
    assert encode.sender_destination(sender, destination) == expected


@pytest.mark.parametrize("bad_sender,bad_destination", [
    (7, 'a'),
    (False, [1, 2, 3]),
    (b'\xff', 60),
])
def test_sender_destination_type_error(bad_sender, bad_destination):
    with pytest.raises(TypeError):
        encode.sender_destination(bad_sender, bad_destination)


@pytest.mark.parametrize("bad_sender,bad_destination", [
    (20, 50),
    (90, 100),
    (125, 0),
])
def test_sender_destination_encode_error(bad_sender, bad_destination):
    with pytest.raises(EncodeError):
        encode.sender_destination(bad_sender, bad_destination)


@pytest.mark.parametrize("function,length,expected", [
    (7, 31, b'\xff'),
    (3, 24, b'x'),
    (4, 8, b'\x90'),
])
def test_function_length_ok(function, length, expected):
    assert encode.function_length(function, length) == expected


@pytest.mark.parametrize("bad_function,bad_length", [
    (7, 'a'),
    (False, [1, 2, 3]),
    (b'\xff', 60),
])
def test_function_length_type_error(bad_function, bad_length):
    with pytest.raises(TypeError):
        encode.function_length(bad_function, bad_length)


@pytest.mark.parametrize("bad_function,bad_length", [
    (20, 50),
    (90, 100),
    (1245, 5),
])
def test_function_length_encode_error(bad_function, bad_length):
    with pytest.raises(EncodeError):
        encode.function_length(bad_function, bad_length)


@pytest.mark.parametrize("bytes_chain,expected", [
    (b'\x1e\xfc\x51\xf7', b'\x9e'),
    (b'\x7f\x12\xc9\xe2', b'\xc4'),
    (b'\xf9\xc2\x96\xa4\xe2', b')'),
])
def test_make_checksum_ok(bytes_chain, expected):
    assert encode.make_checksum(bytes_chain) == expected


@pytest.mark.parametrize("bad_chain", [
    (b'\xff', (7, 28)),
    ('adfsdfc',),
    (False,),
])
def test_make_checksum_type_error(bad_chain):
    with pytest.raises(TypeError):
        encode.make_checksum(1)
