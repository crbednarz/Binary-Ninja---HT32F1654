import struct
from binaryninja import Architecture, BinaryReader, BinaryView
from binaryninja.enums import SectionSemantics, SegmentFlag, SymbolType
from binaryninja.types import Symbol
from .ht32f1654_specs import INTERRUPT_TABLE, HARDWARE_REGISTERS


class HT32F1654View(BinaryView):
    name = "HT32F1654"
    long_name = "HT32F1654 Flash Application"

    def __init__(self, data):
        BinaryView.__init__(self, file_metadata=data.file, parent_view=data)
        self.platform = Architecture["thumb2"].standalone_platform
        self._parse_format(data)

    @classmethod
    def is_valid_for_data(self, data):
        minimum_header_size = len(INTERRUPT_TABLE) * 4 + 4

        if len(data) < minimum_header_size:
            return False
        
        reader = BinaryReader(data)
        stack_pointer = reader.read32()
        if stack_pointer < 0x20000000 or stack_pointer >= 0x20004000:
            return False
        
        reset = reader.read32()
        if reset > 0xFFFF:
            return False

        return True
 
    def _parse_format(self, data):
        self.load_address = self.get_address_input("Base Address", "Base Address")
        reader = BinaryReader(data)
        reader.seek(4)
        entry_point = reader.read32() & ~1
        self.add_entry_point(entry_point)

        # SRAM
        self.add_auto_segment(0x20000000, 0x4000, 0, 0, SegmentFlag.SegmentReadable | SegmentFlag.SegmentWritable | SegmentFlag.SegmentExecutable)
        
        # Flash
        self.add_auto_segment(self.load_address, len(data), 0, len(data), SegmentFlag.SegmentReadable | SegmentFlag.SegmentExecutable)

        self._add_hardware_registers()
        self._add_interrupt_symbols(data)
        return True
    
    def _add_hardware_registers(self):
        for address, name in HARDWARE_REGISTERS.items():
            symbol = Symbol(SymbolType.DataSymbol, address, name)
            self.define_auto_symbol(symbol)

    def _add_interrupt_symbols(self, data):
        reader = BinaryReader(data)
        
        # Skip stack pointer
        reader.seek(4)

        for interrupt in INTERRUPT_TABLE:
            address = reader.read32() & ~1

            if address != 0:
                symbol = Symbol(SymbolType.FunctionSymbol, address, interrupt)
                self.define_auto_symbol(symbol)
                self.add_function(address)
