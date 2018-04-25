import pytest

from ClaptonBase.containers import MemoInstance, Node, Package
from ClaptonBase.exceptions import (ChecksumException, EncodeError,
                                    InvalidPackage, NodeNotExists)
from ClaptonBase.serial_interface import SerialInterface


@pytest.fixture
def memo_instance():
    return MemoInstance(
        node=0,
        instance='RAM',
        start=123,
        timestamp=12345436234.0,
        data=b'\x01\x02\x03\x04\x05\x06'
    )


class TestPackage(object):

    @pytest.mark.parametrize("bytes_chain,expected", [
        (b'\x05\x00\xfb', (0, 5, 0, b'')),
        (b',0\x05\x14\x8b', (2, 12, 1, b'\x05\x14')),
        (b'\x9eX\x00\xff\xff\x0c', (9, 14, 2, b'\x00\xff\xff')),
        (b'\xa2p\t\x10\xd5', (10, 2, 3, b'\t\x10')),
        (b'L\x98\xf0\xe3\xc1\x88', (4, 12, 4, b'\xf0\xe3\xc1')),
        (b';\xe0\xe5', (3, 11, 7, b'')),
    ])
    def test_init_with_bytes_chain_ok(self, bytes_chain, expected):
        valid_package = Package(bytes_chain=bytes_chain)

        assert (valid_package.sender,
                valid_package.destination,
                valid_package.function,
                valid_package.data) == expected


    @pytest.mark.parametrize("bytes_chain", [
        b'\x05\x00\x05\xfb',
        b',0\x05\x14\01\x8b',
        b'\x9eX\x00\xff\x14\xff\x0c',
        b'\xa2p\t\x10\xd5\xad',
        b'L\x98\xf0\xe3\xc1\xae\x88',
        b';\xe0\xe5\xfc',
    ])
    def test_init_with_bytes_raises_checksum_error(self, bytes_chain):
        with pytest.raises(ChecksumException):
            Package(bytes_chain=bytes_chain)

    @pytest.mark.parametrize("sender,destination,function,data,expected", [
        (0, 5, 0, b'', b'\x05\x00\xfb'),
        (2, 12, 1, b'\x05\x14', b',0\x05\x14\x8b'),
        (9, 14, 2, b'\x00\xff\xff', b'\x9eX\x00\xff\xff\x0c'),
        (10, 2, 3, b'\t\x10', b'\xa2p\t\x10\xd5'),
        (4, 12, 4, b'\xf0\xe3\xc1', b'L\x98\xf0\xe3\xc1\x88'),
        (3, 11, 7, b'', b';\xe0\xe5'),
    ])
    def test_init_to_send_ok(self, sender, destination, function, data, expected):
        valid_package = Package(sender=sender,
                                destination=destination,
                                function=function,
                                data=data)
        assert valid_package.bytes_chain == expected


    @pytest.mark.parametrize("sender,destination,function,data", [
        (56, 5, 0, b''),
        (2, 23, 1, b'\x05\x14'),
        (9, 14, 45, b'\x00\xff\xff'),
        (9, 14, 3, bytes(40)),
    ])
    def test_to_send_raises_encode_error(self, sender, destination, function, data):
        with pytest.raises(EncodeError):
            Package(sender=sender,
                    destination=destination,
                    function=function,
                    data=data)

    @pytest.mark.parametrize("sender,destination,function,data", [
        (0, 5, 0, b'\x05\x14'),
        (2, 12, 1, b'\x05'),
        (9, 14, 2, b'\x00'),
        (10, 2, 3, b'\t'),
        (4, 12, 4, b'\xf0'),
        (3, 11, 7, b'\xff'),
    ])
    def test_to_send_raises_invalid_package(self, sender, destination, function, data):
        with pytest.raises(InvalidPackage):
            Package(sender=sender,
                    destination=destination,
                    function=function,
                    data=data)

    @pytest.mark.parametrize("sender,destination,function,data", [
        (None, 5, 0, b''),
        (2, None, 1, b'\x05\x14'),
        (9, 14, None, b'\x00\xff\xff'),
        (10, 2, 3, None),
    ])
    def test_init_raises_attribute_error(self, sender, destination, function, data):
        with pytest.raises(AttributeError):
            Package(sender=sender,
                    destination=destination,
                    function=function,
                    data=data)


class TestMemoInstance(object):

    @pytest.mark.parametrize("node,instance,start,timestamp,data", [
        (0, 'RAM', 0, 1235643.0, b'\x05\x00\xfb'),
        (12, 'RAM', 100, 1235643.0, b',0\x05\x14\x8b'),
        (8, 'EEPROM', 204, 1235643.0, b'\x9eX\x00\xff\xff\x0c'),
        (2, 'EEPROM', 21, 1235643.0, b'\xa2p\t\x10\xd5'),
        (5, 'RAM', 92, 1235643.0, b'L\x98\xf0\xe3\xc1\x88'),
        (14, 'EEPROM', 73, 1235643.0, b';\xe0\xe5'),
    ])
    def test_init_complete_ok(self, node, instance, start, timestamp, data):
        memo = MemoInstance(node=node,
                            instance=instance,
                            start=start,
                            timestamp=timestamp,
                            data=data)
        assert isinstance(memo, MemoInstance)

    @pytest.mark.parametrize("node,instance,start", [
        (0, 'RAM', 0),
        (12, 'RAM', 100),
        (8, 'EEPROM', 204),
        (2, 'EEPROM', 21),
        (5, 'RAM', 92),
        (14, 'EEPROM', 73),
    ])
    def test_init_incomplete_ok(self, node, instance, start):
        memo = MemoInstance(node=node,
                            instance=instance,
                            start=start)
        assert isinstance(memo, MemoInstance)

    @pytest.mark.parametrize("node,instance,start,timestamp,data,expected", [
        (0, 'RAM', 0, 1235643.0, b'\x05\x00\xfb', '0_RAM_0\n1235643.0\n0500fb'),
        (12, 'RAM', 100, 1235643.0, b'\x05\x14\x8b', '12_RAM_100\n1235643.0\n05148b'),
        (8, 'EEPROM', 204, 1235643.0, b'\xff\x0c', '8_EEPROM_204\n1235643.0\nff0c'),
        (2, 'EEPROM', 21, 1235643.0, b'\x10\xd5', '2_EEPROM_21\n1235643.0\n10d5'),
        (5, 'RAM', 92, 1235643.0, b'\xe3\xc1\x88', '5_RAM_92\n1235643.0\ne3c188'),
        (14, 'EEPROM', 73, 1235643.0, b';\xe0\xe5', '14_EEPROM_73\n1235643.0\n3be0e5'),
    ])
    def test_as_msg(self, node, instance, start, timestamp, data, expected):
        m = MemoInstance(node=node,
                         instance=instance,
                         start=start,
                         timestamp=timestamp,
                         data=data)

        assert m.as_msg() == expected

    @pytest.mark.parametrize("index,expected", [
        (123, b'\x01'),
        (124, b'\x02'),
        (125, b'\x03'),
        (126, b'\x04'),
        (127, b'\x05'),
        (128, b'\x06'),
        (100, None),
    ])
    def test_get(self, memo_instance, index, expected):
        assert memo_instance.get(index) == expected

    @pytest.mark.parametrize("node,instance,start,data", [
        (0, 'AM', 0, b''),
        (12, 'RAM', 0, 134),
        (8, 'EEPROM', 0, 'asd'),
        (51, 'RAM', 0, b'\xac'),
        (10, 'EOM', 0, b'\xff'),
    ])
    def test_raises_attribute_error(self, node, instance, start, data):
        with pytest.raises(AttributeError):
            MemoInstance(node=node,
                         instance=instance,
                         start=start,
                         data=data)


class TestNode(object):

    @pytest.mark.parametrize("lan_dir,ser", [
        (0, SerialInterface()),
        (12, SerialInterface()),
        (8, SerialInterface()),
    ])
    def test_init_ok(self, lan_dir, ser):
        node = Node(lan_dir=lan_dir, ser=ser)
        assert isinstance(node, Node)

    @pytest.mark.parametrize("lan_dir,ser", [
        (60, SerialInterface()),
        ('as', SerialInterface()),
        (-5, SerialInterface()),
    ])
    def test_init_raises_type_error(self, lan_dir, ser):
        with pytest.raises(TypeError):
            Node(lan_dir=lan_dir, ser=ser)

    @pytest.mark.parametrize("status", [1, 2, 3, 4, ])
    def test_set_status_ok(self, node, status):
        node.status = status
        assert node.status == status

    @pytest.mark.parametrize("status", ['a', None, b'\xff', ])
    def test_set_status_raises_type_error(self, node, status):
        with pytest.raises(TypeError):
            node.status = status

    def test_identify_ok(self, virtual_node):
        virtual_node.identify()
        assert virtual_node.status == 1

    @pytest.mark.parametrize("rta", [
        b'j\x10\x03\x91\x08h\x8a\x1e\x91\x96\xb3',
        b'y\x10\xbdy\xd1\x02\xa8\\<\x8c\xa2',
        b'\x08\x10\x0f\xf7\x10\x17{\x9f\x82\xee1',
        b'\x1a\x10\r\x19\xdd\x066\xa8YGO',
        b'~\x18}s\x91\x99\xfd\xfb\xd2C\x9d\xac(yY',
        b'[\x10\xde\xa7\x14\xab\xc6=\x93\x883',
    ])
    def test_identify_with_rta_ok(self, node, rta):
        node.identify(rta_bytes_chain=rta)
        assert node.status == 1

    def test_identify_raises_node_not_exists(self, ser_raises_write_exception):
        with pytest.raises(NodeNotExists):
            node = Node(lan_dir=1, ser=ser_raises_write_exception)
            node.identify()

    # @pytest.mark.parametrize("rta", [
        # b'j\x10\x03\x08h\x8a\x1e\x91\x96\xb3',
        # b'y\x10\xbdy\x02\xa8\\<\x8c\xa2',
        # b'\x08\x10\x0f\x10\x17{\x9f\x82\xee1',
        # b'\x1a\x10\x19\xdd\x066\xa8YGO',
        # b'~\x18}s\x99\xfd\xfb\xd2C\x9d\xac(yY',
        # b'[\x10\xde\x14\xab\xc6=\x93\x883',
    # ])
    # def test_identify_raises_invalid_package(self, node, rta):
        # with pytest.raises(InvalidPackage):
            # node.identify(rta_bytes_chain=rta)

    @pytest.mark.parametrize("start,length,instance", [
        (0, 8, 'RAM'),
        (100, 20, 'RAM'),
        (67, 15, 'RAM'),
        (0, 12, 'EEPROM'),
        (51, 1, 'EEPROM'),
        (7, 19, 'EEPROM'),
    ])
    def test_read_memo_ok(self, virtual_node, start, length, instance):
        memo = virtual_node._read_memo(start, length, instance)
        assert isinstance(memo, MemoInstance)

    @pytest.mark.parametrize("start,length,instance", [
        (0, 8, 'RA'),
        (100, 20, 'EEPRO'),
        (67, 15, 'RAMA'),
    ])
    def test_read_memo_raises_key_error(self, node, start, length, instance):
        with pytest.raises(KeyError):
            node._read_memo(start, length, instance)

    @pytest.mark.parametrize("start,length,instance", [
        (0, 260, 'RAM'),
        (1000, 20, 'EEPROM'),
        (67, 1231, 'RAM'),
        (999, 15, 'RAM'),
    ])
    def test_read_memo_raises_invalid_package(self, node, start, length, instance):
        with pytest.raises(InvalidPackage):
            node._read_memo(start, length, instance)

    @pytest.mark.parametrize("start,data,instance,expected", [
        (61, b',\xdd\xd1?\xa4\xe2\xc9\xf6O', 'RAM', b'\x10@\xb0'),
        (73, b'\xbbU\xa0\xf7&\xbf\x80\x0b\x8c', 'EEPROM', b'\x10\x80p'),
        (246, b'\xa16\xa5\xb3\xa4\x00\xfd\xdf\xa3', 'RAM', b'\x10@\xb0'),
        (200, b'\xa5U\x0f\x98j+', 'RAM', b'\x10@\xb0'),
        (174, b'\xed\xd7', 'RAM', b'\x10@\xb0'),
    ])
    def test_write_memo_ok(self, virtual_node, start, data, instance, expected):
        writed, answer = virtual_node._write_memo(start, data, instance)
        assert answer.bytes_chain == expected

    @pytest.mark.parametrize("start,data,instance", [
        (300, b'\x7f19@\x98\x9f\x9c\xa5', 'RAM'),
        (270, b'\xc5\x88\x84', 'RAM'),
        (256, b'', 'EEPROM'),
        (1000, b'\x1d\x83', 'EEPROM'),
        (-50, b'@l\xb5\x19\x7f\xa3\xf7\x17', 'RAM'),
    ])
    def test_write_memo_raises_invalid_package(self, node, start, data, instance):
        with pytest.raises(InvalidPackage):
            node._write_memo(start, data, instance)

    @pytest.mark.parametrize("start,data,instance", [
        (0, b'\x7f19@\x98\x9f\x9c\xa5', 'RAM1'),
        (0, b'\xc5\x88\x84', 'RAM2'),
        (2, b'', 'EEPROM3'),
        (0, b'\x1d\x83', 'EEPROM3'),
        (5, b'@l\xb5\x19\x7f\xa3\xf7\x17', 'RAM3'),
    ])
    def test_write_memo_raises_key_error(self, node, start, data, instance):
        with pytest.raises(KeyError):
            node._write_memo(start, data, instance)

    @pytest.mark.parametrize("start,data,instance", [
        (0, 123, 'RAM1'),
        (0, 'abv', 'RAM2'),
        (2, None, 'EEPROM3'),
        (0, 1.2, 'EEPROM3'),
        (5, [1, 2, 3], 'RAM3'),
    ])
    def test_write_memo_raises_type_error(self, node, start, data, instance):
        with pytest.raises(TypeError):
            node._write_memo(start, data, instance)
