# BOM Manager - Quick Start Guide

## Get Started in 5 Minutes

### Step 1: Run the Application

**Linux/macOS:**
```bash
python3 bom_manager.py
```

**Windows:**
```cmd
python bom_manager.py
```

The application window will open with four tabs: Products, Components, BOM Editor, and Cost Analysis.

### Step 2: Create Your First Product

1. Click the **"Products"** tab
2. Enter a part number: `PCB-001`
3. Enter description: `Main Control Board`
4. Click **"Add Product"**

### Step 3: Add Some Components

1. Click the **"Components"** tab
2. Add a resistor:
   - Mfg Part Number: `RC0805FR-0710KL`
   - Manufacturer: `Yageo`
   - Description: `10K Resistor 0805`
   - Category: `Resistor`
   - Distributor: `Digikey`
   - Dist. Part Number: `311-10.0KCRCT-ND`
   - Unit Cost: `0.10`
   - Click **"Add Component"**

3. Add a capacitor:
   - Mfg Part Number: `GRM21BR61E106KA73L`
   - Manufacturer: `Murata`
   - Description: `10uF 25V X5R 0805`
   - Category: `Capacitor`
   - Distributor: `Digikey`
   - Unit Cost: `0.25`
   - Click **"Add Component"**

### Step 4: Build Your BOM

1. Click the **"BOM Editor"** tab
2. Select product: `PCB-001 - Main Control Board`
3. Add the resistor:
   - Select: `RC0805FR-0710KL (Yageo)`
   - Quantity: `5`
   - Ref Des: `R1,R2,R3,R4,R5`
   - Click **"Add Component"**

4. Add the capacitor:
   - Select: `GRM21BR61E106KA73L (Murata)`
   - Quantity: `2`
   - Ref Des: `C1,C2`
   - Click **"Add Component"**

### Step 5: Calculate Costs

1. Click the **"Cost Analysis"** tab
2. Select product: `PCB-001 - Main Control Board`
3. Enter quantity: `10` (for 10 boards)
4. Click **"Calculate Cost"**

You'll see:
- Total cost for 10 boards
- Breakdown showing:
  - 50 resistors @ $0.10 = $5.00
  - 20 capacitors @ $0.25 = $5.00
  - **Total: $10.00**

### Step 6: Export Your BOM

1. Stay in the **"BOM Editor"** tab
2. Make sure your product is selected
3. Go to **File → Export BOM to CSV**
4. Choose where to save the file
5. Open it in Excel or any spreadsheet program

## Real-World Example: Power Supply Assembly

Let's build a complete power supply with sub-assemblies.

### Create Products
1. `PSU-001` - Complete Power Supply
2. `PCB-PSU-001` - Power Supply PCB
3. `CABLE-001` - Power Cable Assembly

### Add Components for PCB-PSU-001
- LM317 voltage regulator
- Resistors (various)
- Capacitors (various)
- Heat sink
- Mounting hardware

### Add Components for CABLE-001
- Power cable
- Connector housing
- Pins
- Heat shrink

### Add Components for PSU-001
- Enclosure
- Fan
- Mounting screws
- Label

### Build the Hierarchy
1. Add components to PCB-PSU-001
2. Add components to CABLE-001
3. In PSU-001, add:
   - PCB-PSU-001 as sub-assembly (qty: 1)
   - CABLE-001 as sub-assembly (qty: 1)
   - Plus enclosure, fan, etc. as components

### Analyze Total Cost
The system will automatically:
- Calculate PCB-PSU-001 cost
- Calculate CABLE-001 cost
- Add all direct components
- Give you total PSU-001 cost

### Export Flattened BOM
Click "Export Flattened BOM" to get a purchasing list showing:
- All resistors needed (combined from all assemblies)
- All capacitors needed
- All hardware
- Everything in one list with total quantities

## Tips for Success

### 1. Organize Your Products
```
Top-level assemblies:    ASSY-XXX
PCB assemblies:          PCB-XXX
Mechanical assemblies:   MECH-XXX
Cable assemblies:        CABLE-XXX
```

### 2. Use Consistent Categories
```
Resistor
Capacitor
IC
Connector
Mechanical
Hardware
Cable
```

### 3. Reference Designators
Good: `R1,R2,R3` or `R1-R10`
Better: Group by value: `R1-R5 (10K), R6-R8 (1K)`

### 4. Update Costs Regularly
Set a reminder to update distributor pricing monthly.

### 5. Backup Your Database
Copy `bom_database.db` to a safe location regularly.

## Common Workflows

### Design Change
1. Find product in Products tab
2. Switch to BOM Editor
3. Add/remove components
4. Recalculate costs

### Cost Reduction Analysis
1. Export flattened BOM
2. Sort by total cost in spreadsheet
3. Focus on highest-cost items
4. Find alternatives or negotiate volume pricing

### Quoting a Build
1. Go to Cost Analysis
2. Enter quote quantity
3. Calculate cost
4. Add margin for quote price
5. Export for customer

### Purchasing
1. Export flattened BOM
2. Filter by distributor
3. Create purchase orders by distributor
4. Track lead times

## Next Steps

- Read the full README.md for detailed features
- Explore all four tabs
- Try building a multi-level assembly
- Experiment with cost analysis
- Set up your naming conventions
- Import existing BOMs from CSV

## Need Help?

Common issues:
- **Components not showing in BOM Editor**: Refresh the product list
- **Cost showing $0.00**: Add distributor pricing to components
- **Can't add sub-assembly**: Make sure both products exist first
- **Database locked**: Close other instances of the program

Happy BOM building! 🚀
