# Memory and AXI System Refactoring

This document describes the refactoring of the memory and AXI systems in the Spitchel simulator to address the following limitations:

1. Memory allocated all at once - should be dynamically allocated on write
2. Two AXI interfaces defined separately - lots of code duplication
3. AXI interface incomplete - needs full burst support
4. Overall messy - AXI should be refactored into separate files

## Changes Made

### 1. Dynamic Memory System

Replaced the fixed-size `Memory` class with a new `DynamicMemory` implementation that:

- Allocates memory pages (4KB by default) on-demand when written to
- Uses `std::map<size_t, std::vector<uint8_t>>` to track allocated pages
- Reads from unallocated regions return zero values
- Significantly reduces memory footprint for most applications
- Maintains the same interface for backward compatibility

**Files:**
- `include/dynamic_memory.h` - Header file for DynamicMemory class
- `src/dynamic_memory.cpp` - Implementation of DynamicMemory class

### 2. Generic AXI Interface System

Created a clean, extensible AXI interface system with:

- Abstract `AxiInterface` base class for handling AXI transactions
- `NarrowAxiInterface` implementation for 64-bit AXI interfaces
- `WideAxiInterface` implementation for 512-bit AXI interfaces
- Full AXI4 protocol support including:
  - Burst transactions (FIXED, INCR, WRAP)
  - Byte-level strobes for precise memory updates
  - Proper response handling (OKAY, EXOKAY, SLVERR, DECERR)
  - Support for burst lengths and sizes

**Files:**
- `include/axi_interface.h` - Header file for AXI interface classes
- `src/axi_interface.cpp` - Implementation of AXI interface classes

### 3. Simulation Integration

Updated the `Sim` class to:

- Use `DynamicMemory` instead of fixed `Memory`
- Support multiple AXI interfaces through a vector of unique pointers
- Simplify the simulation loop to iterate through all attached AXI interfaces
- Remove duplicated and messy AXI handling code

**Files:**
- `include/sim.h` - Updated to use DynamicMemory and generic AXI interfaces
- `src/sim.cpp` - Updated implementation

### 4. Loader Updates

Updated the `Loader` class to work with `DynamicMemory`:

**Files:**
- `include/loader.h` - Updated to use DynamicMemory reference
- `src/loader.cpp` - Updated implementation

### 5. Build System

Updated CMakeLists.txt to include the new source files.

**Files:**
- `CMakeLists.txt` - Added dynamic_memory.cpp and axi_interface.cpp

## Benefits

1. **Memory Efficiency**: Only allocates memory when actually used, reducing memory footprint significantly
2. **Cleaner Architecture**: Separated concerns with dedicated AXI interface classes
3. **Extensibility**: Easy to add new AXI interfaces or modify existing ones
4. **Better AXI Compliance**: Proper handling of burst transactions and strobes
5. **Maintainability**: Reduced code duplication and complexity

## Usage

The refactored system automatically creates two AXI interfaces by default:
- A wide AXI interface (512-bit data)
- A narrow AXI interface (64-bit data)

Additional AXI interfaces can be added dynamically using:
```cpp
sim.add_axi_interface(std::make_unique<WideAxiInterface>("custom_wide_axi"));
sim.add_axi_interface(std::make_unique<NarrowAxiInterface>("custom_narrow_axi"));
```

## Implementation Details

### Dynamic Memory

The `DynamicMemory` class divides the address space into pages (default 4KB). When a write occurs to an address:
1. The page containing that address is identified
2. If the page doesn't exist, it's created and initialized with zeros
3. The write is performed on the page

This approach provides significant memory savings for programs that don't use the full address space.

### AXI Interface Implementation

Each AXI interface implementation handles:
1. **Address Channel**: Process read/write address requests
2. **Data Channel**: Handle data transfers with strobe support
3. **Response Channel**: Send appropriate responses for completed transactions
4. **Burst Handling**: Calculate addresses for each transfer in a burst
5. **Strobe Application**: Apply byte-level write enables during writes

The system properly supports AXI4 features including:
- Burst types (FIXED, INCR, WRAP)
- Various burst sizes (1 to 128 bytes)
- Burst lengths (1 to 256 transfers)
- Byte-level write strobes
- Response types (OKAY, EXOKAY, SLVERR, DECERR)

Note: For wrap bursts, AXI protocol limits the maximum wrap length to 16 transfers regardless of the burst length field.

## Future Improvements

Potential areas for future enhancement:
1. Add support for exclusive access (EXOKAY responses)
2. Implement cache and memory type handling
3. Add performance monitoring and statistics
4. Support for additional AXI interface widths
5. Integration with memory protection mechanisms