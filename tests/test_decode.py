import pytest
from ClaptonBase import decode
from ClaptonBase.exceptions import DecodeError


@pytest.mark.parametrize("head_byte,expected", [
    (b'\xff', (15, 15)),
    (b'\x7e', (7, 14)),
    (b'\x92', (9, 2))
])
def test_sender_destination_ok(head_byte, expected):
    assert decode.sender_destination(head_byte) == expected

@pytest.mark.parametrize("bad_byte", [(7, 'a', False, [1, 2, 3])])
def test_sender_destination_raises_type_error(bad_byte):
    with pytest.raises(TypeError):
        decode.sender_destination(bad_byte)

@pytest.mark.parametrize("bad_byte", [b'\xff\x03', b'\x12\x90', b''])
def test_sender_destination_raises_decode_error(bad_byte):
    with pytest.raises(DecodeError):
        decode.sender_destination(bad_byte)

@pytest.mark.parametrize("head_byte,expected", [
    (b'\xff', (7, 31)),
    (b'x', (3, 24)),
    (b'\x90', (4, 8)),
])
def test_function_length_ok(head_byte, expected):
    assert decode.function_length(head_byte), expected

@pytest.mark.parametrize("bad_byte", [(7, 'a', False, [1, 2, 3])])
def test_function_length_raises_type_error(bad_byte):
    with pytest.raises(TypeError):
        decode.function_length(bad_byte)

@pytest.mark.parametrize("bad_byte", [b'\xff\x03', b'\x12\x90', b''])
def test_function_length_raises_decode_error(bad_byte):
    with pytest.raises(DecodeError):
        decode.sender_destination(bad_byte)

@pytest.mark.parametrize("bytes_chain", [
    b'\x1e\xfc\x51\xf7\x9e',
    b'\x7f\x12\xc9\xe2\xc4',
    b'\xf9\xc2\x96\xa4\xe2)',
])
def test_validate_checksum_true(bytes_chain):
    assert decode.validate_checksum(bytes_chain)

@pytest.mark.parametrize("bytes_chain", [
    b'\x1e\xfc\x51\xf7',
    b'\x7f\x12\xc9\xe2',
    b'\xf9\xc2\x96\xa4',
])
def test_validate_checksum_false(bytes_chain):
    assert not decode.validate_checksum(bytes_chain)

@pytest.mark.parametrize("bad_chain", [
    (b'\xff', (7, 28)),
    ('adfsdfc',),
    (False, 1, 12),
])
def test_validate_checksum_type_error(bad_chain):
    with pytest.raises(TypeError):
        decode.validate_checksum(bad_chain)
