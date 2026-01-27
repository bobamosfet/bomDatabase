# BOM Manager - Bill of Materials Management System

A comprehensive, cross-platform GUI application for managing hierarchical bills of materials (BOMs) with cost tracking, built in Python with tkinter.

## Features

### Core Functionality
- **Product Management**: Create and manage product part numbers with descriptions, revisions, and notes
- **Component Database**: Store detailed component information including manufacturer, distributor, and pricing
- **Hierarchical BOMs**: Build complex BOMs with nested sub-assemblies
- **Cost Analysis**: Automatic cost calculation with detailed breakdowns
- **Flattened BOMs**: Generate consolidated parts lists across all sub-assemblies
- **Import/Export**: CSV import and export capabilities

### Database Schema

The application uses SQLite with the following structure:

#### Products Table
- Part Number (unique identifier)
- Description
- Revision
- Created/Modified dates
- Notes

#### Components Table
- Manufacturing Part Number
- Manufacturer
- Description
- Category
- Unit of Measure
- Assembly flag
- Notes

#### Component Sources Table
- Distributor
- Distributor Part Number
- Unit Cost
- Minimum Order Quantity
- Lead Time
- Last Updated

#### BOM Entries Table
- Links products to components
- Quantity
- Reference Designators
- Do Not Populate flag
- Notes

#### Sub-Assemblies Table
- Links products to other products (nested BOMs)
- Quantity
- Reference Designators
- Notes

## Installation

### Prerequisites

Python 3.6 or higher is required. The application uses only standard Python libraries:
- tkinter (usually comes with Python)
- sqlite3 (included with Python)
- csv (included with Python)

### Linux Installation

1. **Check Python version:**
```bash
python3 --version
```

2. **Install tkinter if needed (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install python3-tk
```

3. **For Fedora/RHEL:**
```bash
sudo dnf install python3-tkinter
```

4. **Download and run:**
```bash
chmod +x bom_manager.py
python3 bom_manager.py
```

### Windows Installation

1. **Download Python from python.org** (tkinter is included by default)

2. **Run the application:**
```cmd
python bom_manager.py
```

Or double-click the file if Python is associated with .py files.

### macOS Installation

1. **Check Python version:**
```bash
python3 --version
```

2. **Install tkinter if needed (using Homebrew):**
```bash
brew install python-tk
```

3. **Run the application:**
```bash
python3 bom_manager.py
```

## Usage Guide

### 1. Managing Products

**To create a new product:**
1. Go to the "Products" tab
2. Enter the part number (required)
3. Enter description, revision, and notes (optional)
4. Click "Add Product"

Products represent top-level assemblies or sub-assemblies that can contain components and other products.

### 2. Managing Components

**To add a component:**
1. Go to the "Components" tab
2. Enter manufacturer part number and manufacturer (required)
3. Enter description and category (optional)
4. Enter distributor information and cost (optional)
5. Click "Add Component"

Components represent individual parts that can be purchased from distributors.

### 3. Building a BOM

**To create a bill of materials:**
1. Go to the "BOM Editor" tab
2. Select a product from the dropdown
3. Add components:
   - Select a component
   - Enter quantity
   - Enter reference designators (e.g., "R1, R2, R3")
   - Click "Add Component"
4. Add sub-assemblies:
   - Select another product
   - Enter quantity
   - Click "Add Sub-Assembly"

**Example Workflow:**

Let's say you're building a power supply (PS-001) that uses a PCB assembly (PCB-001):

1. Create products:
   - PS-001 (Power Supply)
   - PCB-001 (PCB Assembly)

2. Add components to PCB-001:
   - Resistor 10K (qty: 5, ref: R1-R5)
   - Capacitor 100uF (qty: 2, ref: C1, C2)
   - IC LM317 (qty: 1, ref: U1)

3. Add PCB-001 as sub-assembly to PS-001:
   - PCB-001 (qty: 1)
   - Also add enclosure, screws, etc.

### 4. Cost Analysis

**To analyze costs:**
1. Go to the "Cost Analysis" tab
2. Select a product
3. Enter build quantity
4. Click "Calculate Cost"

The system will:
- Calculate total cost including all sub-assemblies
- Show detailed breakdown by component
- Recursively calculate costs for nested assemblies

**Export Flattened BOM:**
- Shows total quantities needed across all sub-assemblies
- Useful for purchasing and inventory management
- Exports to CSV format

### 5. Import/Export

**Export BOM to CSV:**
1. Select a product in the BOM Editor
2. File → Export BOM to CSV
3. Choose location and filename

**Import from CSV:**
- File → Import BOM from CSV
- CSV should contain columns matching the database schema
- Use exported files as templates

## Advanced Features

### Hierarchical Cost Calculation

The system automatically calculates costs recursively:
```
Power Supply (PS-001)
├── Enclosure: $5.00
├── PCB Assembly (PCB-001)
│   ├── Resistors (5x): $0.50
│   ├── Capacitors (2x): $1.00
│   └── IC (1x): $3.50
└── Hardware Kit: $2.00

Total: $12.00
```

### Reference Designators

Use reference designators to track component placement:
- Single: "R1"
- Multiple: "R1, R2, R3"
- Range: "R1-R10"
- Mixed: "R1, R3-R5, R10"

### Do Not Populate (DNP)

Mark components as DNP for:
- Optional features
- Different build variants
- Components to be added later

## Database File

The application creates `bom_database.db` in the same directory as the script. This file contains all your data and can be:
- Backed up regularly
- Shared with team members
- Version controlled

To start fresh, simply delete or rename this file.

## Tips and Best Practices

### Naming Conventions
- **Products**: Use meaningful part numbers (e.g., "PCB-001-A", "ASSY-PSU-001")
- **Revisions**: Start with "A" and increment (A, B, C...)
- **Categories**: Use consistent categories (e.g., "Resistor", "Capacitor", "IC")

### Component Management
- Always include manufacturer name to avoid ambiguity
- Keep distributor information updated
- Use consistent unit of measure (EA, PCS, FT, etc.)

### BOM Organization
- Build smaller sub-assemblies first
- Use reference designators consistently
- Add notes for special handling or sourcing requirements

### Cost Tracking
- Update component costs regularly
- Use minimum order quantities for accuracy
- Consider lead times in planning

## Troubleshooting

### "No module named 'tkinter'"
**Linux:** Install python3-tk package
**Windows:** Reinstall Python with "tcl/tk and IDLE" option checked
**macOS:** Install python-tk via Homebrew

### Database locked error
Close any other instances of the application accessing the same database.

### Missing components in BOM
Ensure components are added to the database before adding them to a BOM.

### Cost calculation shows $0.00
Verify that component sources with unit costs are entered for all components.

## Future Enhancements

Possible additions to consider:
- Advanced import from EDA tools (Altium, KiCAD)
- Multi-currency support
- Supplier comparison
- Inventory tracking
- Purchase order generation
- Drawing/datasheet attachments
- Change tracking/approval workflow
- Web-based interface
- API for integration with other systems

## Technical Details

### Database Schema Diagram
```
products
├── product_id (PK)
├── part_number (UNIQUE)
├── description
├── revision
└── notes

components
├── component_id (PK)
├── mfg_part_number
├── manufacturer
├── description
└── category

component_sources
├── source_id (PK)
├── component_id (FK)
├── distributor
├── distributor_part_number
└── unit_cost

bom_entries
├── entry_id (PK)
├── product_id (FK)
├── component_id (FK)
├── quantity
└── reference_designators

sub_assemblies
├── sub_assembly_id (PK)
├── parent_product_id (FK)
├── child_product_id (FK)
└── quantity
```

### File Structure
```
bom_manager.py      # Main application
bom_database.db     # SQLite database (created on first run)
README.md           # This file
```

## License

This software is provided as-is for use and modification. Feel free to adapt it to your needs.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review the database schema
3. Examine error messages in the console
4. Check file permissions for database access

## Version History

- **v1.0** - Initial release
  - Core BOM management
  - Hierarchical assemblies
  - Cost calculation
  - CSV import/export
  - Cross-platform GUI
