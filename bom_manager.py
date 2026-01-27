#!/usr/bin/env python3
"""
BOM Manager - Bill of Materials Management System
A comprehensive tool for managing hierarchical bills of materials with cost tracking
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime
import csv
import json
from decimal import Decimal


class BOMDatabase:
    """Handles all database operations for the BOM system"""
    
    def __init__(self, db_path="bom_database.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def create_tables(self):
        """Create database schema"""
        # Products table - top-level assemblies
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_number TEXT UNIQUE NOT NULL,
                description TEXT,
                revision TEXT,
                created_date TEXT,
                modified_date TEXT,
                notes TEXT
            )
        """)
        
        # Components table - individual parts and sub-assemblies
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS components (
                component_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mfg_part_number TEXT NOT NULL,
                manufacturer TEXT,
                description TEXT,
                category TEXT,
                unit_of_measure TEXT DEFAULT 'EA',
                is_assembly INTEGER DEFAULT 0,
                notes TEXT,
                UNIQUE(mfg_part_number, manufacturer)
            )
        """)
        
        # Component sources - where to buy components
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS component_sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_id INTEGER,
                distributor TEXT,
                distributor_part_number TEXT,
                unit_cost REAL,
                minimum_order_qty INTEGER DEFAULT 1,
                lead_time_days INTEGER,
                last_updated TEXT,
                FOREIGN KEY (component_id) REFERENCES components(component_id)
            )
        """)
        
        # BOM entries - links products to components
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bom_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                component_id INTEGER,
                quantity REAL NOT NULL,
                reference_designators TEXT,
                do_not_populate INTEGER DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (product_id) REFERENCES products(product_id),
                FOREIGN KEY (component_id) REFERENCES components(component_id)
            )
        """)
        
        # Sub-assembly references - products can contain other products
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_assemblies (
                sub_assembly_id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_product_id INTEGER,
                child_product_id INTEGER,
                quantity REAL NOT NULL,
                reference_designators TEXT,
                notes TEXT,
                FOREIGN KEY (parent_product_id) REFERENCES products(product_id),
                FOREIGN KEY (child_product_id) REFERENCES products(product_id)
            )
        """)
        
        self.conn.commit()
    
    def add_product(self, part_number, description="", revision="A", notes=""):
        """Create a new product"""
        try:
            now = datetime.now().isoformat()
            self.cursor.execute("""
                INSERT INTO products (part_number, description, revision, created_date, modified_date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (part_number, description, revision, now, now, notes))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def get_product(self, part_number):
        """Get product by part number"""
        self.cursor.execute("SELECT * FROM products WHERE part_number = ?", (part_number,))
        return self.cursor.fetchone()
    
    def get_all_products(self):
        """Get all products"""
        self.cursor.execute("SELECT * FROM products ORDER BY part_number")
        return self.cursor.fetchall()
    
    def add_component(self, mfg_part_number, manufacturer, description="", category="", 
                     unit_of_measure="EA", is_assembly=False, notes=""):
        """Add a component to the database"""
        try:
            self.cursor.execute("""
                INSERT INTO components (mfg_part_number, manufacturer, description, category, 
                                      unit_of_measure, is_assembly, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (mfg_part_number, manufacturer, description, category, unit_of_measure, 
                  1 if is_assembly else 0, notes))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Component already exists, return its ID
            self.cursor.execute("""
                SELECT component_id FROM components 
                WHERE mfg_part_number = ? AND manufacturer = ?
            """, (mfg_part_number, manufacturer))
            result = self.cursor.fetchone()
            return result['component_id'] if result else None
    
    def add_component_source(self, component_id, distributor, distributor_part_number,
                            unit_cost, minimum_order_qty=1, lead_time_days=None):
        """Add a source for a component"""
        now = datetime.now().isoformat()
        self.cursor.execute("""
            INSERT INTO component_sources (component_id, distributor, distributor_part_number,
                                          unit_cost, minimum_order_qty, lead_time_days, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (component_id, distributor, distributor_part_number, unit_cost, 
              minimum_order_qty, lead_time_days, now))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def add_bom_entry(self, product_id, component_id, quantity, reference_designators="", 
                     do_not_populate=False, notes=""):
        """Add a component to a product's BOM"""
        self.cursor.execute("""
            INSERT INTO bom_entries (product_id, component_id, quantity, reference_designators,
                                    do_not_populate, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (product_id, component_id, quantity, reference_designators, 
              1 if do_not_populate else 0, notes))
        self.conn.commit()
        
        # Update product modified date
        now = datetime.now().isoformat()
        self.cursor.execute("UPDATE products SET modified_date = ? WHERE product_id = ?", 
                          (now, product_id))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def add_sub_assembly(self, parent_product_id, child_product_id, quantity, 
                        reference_designators="", notes=""):
        """Add a sub-assembly (another product) to a product's BOM"""
        self.cursor.execute("""
            INSERT INTO sub_assemblies (parent_product_id, child_product_id, quantity,
                                       reference_designators, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (parent_product_id, child_product_id, quantity, reference_designators, notes))
        self.conn.commit()
        
        # Update parent product modified date
        now = datetime.now().isoformat()
        self.cursor.execute("UPDATE products SET modified_date = ? WHERE product_id = ?", 
                          (now, parent_product_id))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_product_bom(self, product_id, include_dnp=False):
        """Get the complete BOM for a product including sub-assemblies"""
        # Get direct components
        dnp_filter = "" if include_dnp else "AND be.do_not_populate = 0"
        self.cursor.execute(f"""
            SELECT 
                c.mfg_part_number,
                c.manufacturer,
                c.description,
                c.category,
                c.unit_of_measure,
                be.quantity,
                be.reference_designators,
                be.do_not_populate,
                be.notes,
                cs.distributor,
                cs.distributor_part_number,
                cs.unit_cost,
                cs.minimum_order_qty,
                cs.lead_time_days,
                'component' as item_type
            FROM bom_entries be
            JOIN components c ON be.component_id = c.component_id
            LEFT JOIN component_sources cs ON c.component_id = cs.component_id
            WHERE be.product_id = ? {dnp_filter}
            ORDER BY be.reference_designators, c.mfg_part_number
        """, (product_id,))
        components = self.cursor.fetchall()
        
        # Get sub-assemblies
        self.cursor.execute("""
            SELECT 
                p.part_number,
                p.description,
                sa.quantity,
                sa.reference_designators,
                sa.notes,
                'sub_assembly' as item_type,
                p.product_id
            FROM sub_assemblies sa
            JOIN products p ON sa.child_product_id = p.product_id
            WHERE sa.parent_product_id = ?
            ORDER BY sa.reference_designators, p.part_number
        """, (product_id,))
        sub_assemblies = self.cursor.fetchall()
        
        return components, sub_assemblies
    
    def calculate_bom_cost(self, product_id, quantity=1, include_dnp=False):
        """Calculate the total cost of a BOM"""
        components, sub_assemblies = self.get_product_bom(product_id, include_dnp)
        
        total_cost = 0.0
        component_costs = []
        
        # Calculate component costs
        for comp in components:
            if comp['unit_cost']:
                comp_total = float(comp['unit_cost']) * float(comp['quantity']) * quantity
                total_cost += comp_total
                component_costs.append({
                    'item': f"{comp['mfg_part_number']} ({comp['manufacturer']})",
                    'quantity': comp['quantity'],
                    'unit_cost': comp['unit_cost'],
                    'total': comp_total
                })
        
        # Calculate sub-assembly costs recursively
        for sub in sub_assemblies:
            sub_cost, _ = self.calculate_bom_cost(sub['product_id'], 
                                                   float(sub['quantity']) * quantity, 
                                                   include_dnp)
            total_cost += sub_cost
            component_costs.append({
                'item': f"[Assembly] {sub['part_number']}",
                'quantity': sub['quantity'],
                'unit_cost': sub_cost / (float(sub['quantity']) * quantity),
                'total': sub_cost
            })
        
        return total_cost, component_costs
    
    def get_flattened_bom(self, product_id, quantity=1, include_dnp=False):
        """Get a flattened BOM with all components from all sub-assemblies"""
        flattened = {}
        
        def flatten_recursive(prod_id, qty):
            components, sub_assemblies = self.get_product_bom(prod_id, include_dnp)
            
            # Add components
            for comp in components:
                key = f"{comp['mfg_part_number']}|{comp['manufacturer']}"
                if key in flattened:
                    flattened[key]['quantity'] += float(comp['quantity']) * qty
                else:
                    flattened[key] = {
                        'mfg_part_number': comp['mfg_part_number'],
                        'manufacturer': comp['manufacturer'],
                        'description': comp['description'],
                        'category': comp['category'],
                        'unit_of_measure': comp['unit_of_measure'],
                        'quantity': float(comp['quantity']) * qty,
                        'distributor': comp['distributor'],
                        'distributor_part_number': comp['distributor_part_number'],
                        'unit_cost': comp['unit_cost'],
                        'do_not_populate': comp['do_not_populate']
                    }
            
            # Recursively flatten sub-assemblies
            for sub in sub_assemblies:
                flatten_recursive(sub['product_id'], float(sub['quantity']) * qty)
        
        flatten_recursive(product_id, quantity)
        return list(flattened.values())
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


class BOMManagerGUI:
    """Main GUI application for BOM management"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("BOM Manager - Bill of Materials System")
        self.root.geometry("1200x800")
        
        self.db = BOMDatabase()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the user interface"""
        # Create menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import BOM from CSV", command=self.import_bom_csv)
        file_menu.add_command(label="Export BOM to CSV", command=self.export_bom_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Products
        self.products_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.products_tab, text="Products")
        self.setup_products_tab()
        
        # Tab 2: Components
        self.components_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.components_tab, text="Components")
        self.setup_components_tab()
        
        # Tab 3: BOM Editor
        self.bom_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.bom_tab, text="BOM Editor")
        self.setup_bom_tab()
        
        # Tab 4: Cost Analysis
        self.cost_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.cost_tab, text="Cost Analysis")
        self.setup_cost_tab()
    
    def setup_products_tab(self):
        """Setup the products management tab"""
        # Top frame for adding new products
        top_frame = ttk.LabelFrame(self.products_tab, text="Add New Product", padding=10)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Part Number:").grid(row=0, column=0, sticky=tk.W)
        self.product_pn_entry = ttk.Entry(top_frame, width=30)
        self.product_pn_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(top_frame, text="Description:").grid(row=0, column=2, sticky=tk.W)
        self.product_desc_entry = ttk.Entry(top_frame, width=50)
        self.product_desc_entry.grid(row=0, column=3, padx=5)
        
        ttk.Label(top_frame, text="Revision:").grid(row=1, column=0, sticky=tk.W)
        self.product_rev_entry = ttk.Entry(top_frame, width=10)
        self.product_rev_entry.insert(0, "A")
        self.product_rev_entry.grid(row=1, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(top_frame, text="Notes:").grid(row=1, column=2, sticky=tk.W)
        self.product_notes_entry = ttk.Entry(top_frame, width=50)
        self.product_notes_entry.grid(row=1, column=3, padx=5)
        
        ttk.Button(top_frame, text="Add Product", 
                  command=self.add_product).grid(row=2, column=1, pady=10)
        
        # Bottom frame for product list
        bottom_frame = ttk.LabelFrame(self.products_tab, text="Existing Products", padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Product treeview
        columns = ('Part Number', 'Description', 'Revision', 'Created', 'Modified')
        self.product_tree = ttk.Treeview(bottom_frame, columns=columns, show='tree headings')
        
        for col in columns:
            self.product_tree.heading(col, text=col)
            self.product_tree.column(col, width=150)
        
        self.product_tree.column('#0', width=0, stretch=tk.NO)
        
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, 
                                 command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        
        self.product_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Refresh", 
                  command=self.refresh_products).pack(side=tk.LEFT, padx=5)
        
        self.refresh_products()
    
    def setup_components_tab(self):
        """Setup the components management tab"""
        # Top frame for adding components
        top_frame = ttk.LabelFrame(self.components_tab, text="Add New Component", padding=10)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Mfg Part Number:").grid(row=0, column=0, sticky=tk.W)
        self.comp_mpn_entry = ttk.Entry(top_frame, width=30)
        self.comp_mpn_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(top_frame, text="Manufacturer:").grid(row=0, column=2, sticky=tk.W)
        self.comp_mfg_entry = ttk.Entry(top_frame, width=30)
        self.comp_mfg_entry.grid(row=0, column=3, padx=5)
        
        ttk.Label(top_frame, text="Description:").grid(row=1, column=0, sticky=tk.W)
        self.comp_desc_entry = ttk.Entry(top_frame, width=30)
        self.comp_desc_entry.grid(row=1, column=1, padx=5)
        
        ttk.Label(top_frame, text="Category:").grid(row=1, column=2, sticky=tk.W)
        self.comp_cat_entry = ttk.Entry(top_frame, width=30)
        self.comp_cat_entry.grid(row=1, column=3, padx=5)
        
        ttk.Label(top_frame, text="Distributor:").grid(row=2, column=0, sticky=tk.W)
        self.comp_dist_entry = ttk.Entry(top_frame, width=30)
        self.comp_dist_entry.grid(row=2, column=1, padx=5)
        
        ttk.Label(top_frame, text="Dist. Part Number:").grid(row=2, column=2, sticky=tk.W)
        self.comp_dpn_entry = ttk.Entry(top_frame, width=30)
        self.comp_dpn_entry.grid(row=2, column=3, padx=5)
        
        ttk.Label(top_frame, text="Unit Cost:").grid(row=3, column=0, sticky=tk.W)
        self.comp_cost_entry = ttk.Entry(top_frame, width=15)
        self.comp_cost_entry.grid(row=3, column=1, padx=5, sticky=tk.W)
        
        ttk.Button(top_frame, text="Add Component", 
                  command=self.add_component).grid(row=4, column=1, pady=10)
        
        # Bottom frame for component list
        bottom_frame = ttk.LabelFrame(self.components_tab, text="Existing Components", padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Component treeview
        columns = ('Mfg Part Number', 'Manufacturer', 'Description', 'Category', 
                  'Distributor', 'Unit Cost')
        self.component_tree = ttk.Treeview(bottom_frame, columns=columns, show='tree headings')
        
        for col in columns:
            self.component_tree.heading(col, text=col)
            self.component_tree.column(col, width=150)
        
        self.component_tree.column('#0', width=0, stretch=tk.NO)
        
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, 
                                 command=self.component_tree.yview)
        self.component_tree.configure(yscrollcommand=scrollbar.set)
        
        self.component_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(bottom_frame, text="Refresh", 
                  command=self.refresh_components).pack(pady=5)
        
        self.refresh_components()
    
    def setup_bom_tab(self):
        """Setup the BOM editor tab"""
        # Top section: Select product
        top_frame = ttk.LabelFrame(self.bom_tab, text="Select Product", padding=10)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Product:").pack(side=tk.LEFT)
        self.bom_product_var = tk.StringVar()
        self.bom_product_combo = ttk.Combobox(top_frame, textvariable=self.bom_product_var,
                                              width=50, state='readonly')
        self.bom_product_combo.pack(side=tk.LEFT, padx=5)
        self.bom_product_combo.bind('<<ComboboxSelected>>', self.load_bom)
        
        ttk.Button(top_frame, text="Refresh Products", 
                  command=self.refresh_bom_products).pack(side=tk.LEFT, padx=5)
        
        # Middle section: Add items to BOM
        add_frame = ttk.LabelFrame(self.bom_tab, text="Add to BOM", padding=10)
        add_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add component
        comp_frame = ttk.Frame(add_frame)
        comp_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(comp_frame, text="Add Component:").grid(row=0, column=0, sticky=tk.W)
        self.bom_comp_var = tk.StringVar()
        self.bom_comp_combo = ttk.Combobox(comp_frame, textvariable=self.bom_comp_var,
                                           width=40, state='readonly')
        self.bom_comp_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(comp_frame, text="Qty:").grid(row=0, column=2)
        self.bom_comp_qty_entry = ttk.Entry(comp_frame, width=10)
        self.bom_comp_qty_entry.insert(0, "1")
        self.bom_comp_qty_entry.grid(row=0, column=3, padx=5)
        
        ttk.Label(comp_frame, text="Ref Des:").grid(row=0, column=4)
        self.bom_comp_ref_entry = ttk.Entry(comp_frame, width=20)
        self.bom_comp_ref_entry.grid(row=0, column=5, padx=5)
        
        ttk.Button(comp_frame, text="Add Component", 
                  command=self.add_to_bom).grid(row=0, column=6, padx=5)
        
        # Add sub-assembly
        sub_frame = ttk.Frame(add_frame)
        sub_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(sub_frame, text="Add Sub-Assembly:").grid(row=0, column=0, sticky=tk.W)
        self.bom_sub_var = tk.StringVar()
        self.bom_sub_combo = ttk.Combobox(sub_frame, textvariable=self.bom_sub_var,
                                          width=40, state='readonly')
        self.bom_sub_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(sub_frame, text="Qty:").grid(row=0, column=2)
        self.bom_sub_qty_entry = ttk.Entry(sub_frame, width=10)
        self.bom_sub_qty_entry.insert(0, "1")
        self.bom_sub_qty_entry.grid(row=0, column=3, padx=5)
        
        ttk.Label(sub_frame, text="Ref Des:").grid(row=0, column=4)
        self.bom_sub_ref_entry = ttk.Entry(sub_frame, width=20)
        self.bom_sub_ref_entry.grid(row=0, column=5, padx=5)
        
        ttk.Button(sub_frame, text="Add Sub-Assembly", 
                  command=self.add_subassembly_to_bom).grid(row=0, column=6, padx=5)
        
        # Bottom section: BOM display
        bottom_frame = ttk.LabelFrame(self.bom_tab, text="Bill of Materials", padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # BOM treeview
        columns = ('Type', 'Part Number', 'Mfr/Product', 'Description', 'Qty', 
                  'Ref Des', 'Distributor', 'Cost')
        self.bom_tree = ttk.Treeview(bottom_frame, columns=columns, show='tree headings')
        
        for col in columns:
            self.bom_tree.heading(col, text=col)
            self.bom_tree.column(col, width=120)
        
        self.bom_tree.column('#0', width=0, stretch=tk.NO)
        
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, 
                                 command=self.bom_tree.yview)
        self.bom_tree.configure(yscrollcommand=scrollbar.set)
        
        self.bom_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.refresh_bom_products()
    
    def setup_cost_tab(self):
        """Setup the cost analysis tab"""
        # Top section: Select product
        top_frame = ttk.LabelFrame(self.cost_tab, text="Cost Analysis", padding=10)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Product:").grid(row=0, column=0, sticky=tk.W)
        self.cost_product_var = tk.StringVar()
        self.cost_product_combo = ttk.Combobox(top_frame, textvariable=self.cost_product_var,
                                               width=50, state='readonly')
        self.cost_product_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(top_frame, text="Quantity:").grid(row=0, column=2)
        self.cost_qty_entry = ttk.Entry(top_frame, width=10)
        self.cost_qty_entry.insert(0, "1")
        self.cost_qty_entry.grid(row=0, column=3, padx=5)
        
        ttk.Button(top_frame, text="Calculate Cost", 
                  command=self.calculate_cost).grid(row=0, column=4, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.cost_tab, text="Cost Breakdown", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Cost summary
        summary_frame = ttk.Frame(results_frame)
        summary_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(summary_frame, text="Total Cost:", font=('TkDefaultFont', 12, 'bold')).pack(side=tk.LEFT)
        self.total_cost_label = ttk.Label(summary_frame, text="$0.00", 
                                          font=('TkDefaultFont', 12, 'bold'))
        self.total_cost_label.pack(side=tk.LEFT, padx=10)
        
        # Detailed breakdown
        columns = ('Item', 'Quantity', 'Unit Cost', 'Total Cost')
        self.cost_tree = ttk.Treeview(results_frame, columns=columns, show='tree headings')
        
        for col in columns:
            self.cost_tree.heading(col, text=col)
            self.cost_tree.column(col, width=200)
        
        self.cost_tree.column('#0', width=0, stretch=tk.NO)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, 
                                 command=self.cost_tree.yview)
        self.cost_tree.configure(yscrollcommand=scrollbar.set)
        
        self.cost_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Export options
        export_frame = ttk.Frame(results_frame)
        export_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(export_frame, text="Export Flattened BOM", 
                  command=self.export_flattened_bom).pack(side=tk.LEFT, padx=5)
        
        # Populate product combo
        self.refresh_cost_products()
    
    def add_product(self):
        """Add a new product"""
        part_number = self.product_pn_entry.get().strip()
        description = self.product_desc_entry.get().strip()
        revision = self.product_rev_entry.get().strip()
        notes = self.product_notes_entry.get().strip()
        
        if not part_number:
            messagebox.showerror("Error", "Part number is required")
            return
        
        product_id = self.db.add_product(part_number, description, revision, notes)
        
        if product_id:
            messagebox.showinfo("Success", f"Product {part_number} added successfully")
            self.product_pn_entry.delete(0, tk.END)
            self.product_desc_entry.delete(0, tk.END)
            self.product_rev_entry.delete(0, tk.END)
            self.product_rev_entry.insert(0, "A")
            self.product_notes_entry.delete(0, tk.END)
            self.refresh_products()
        else:
            messagebox.showerror("Error", "Product already exists or error occurred")
    
    def add_component(self):
        """Add a new component"""
        mpn = self.comp_mpn_entry.get().strip()
        mfg = self.comp_mfg_entry.get().strip()
        desc = self.comp_desc_entry.get().strip()
        cat = self.comp_cat_entry.get().strip()
        dist = self.comp_dist_entry.get().strip()
        dpn = self.comp_dpn_entry.get().strip()
        cost_str = self.comp_cost_entry.get().strip()
        
        if not mpn or not mfg:
            messagebox.showerror("Error", "Manufacturer part number and manufacturer are required")
            return
        
        try:
            cost = float(cost_str) if cost_str else None
        except ValueError:
            messagebox.showerror("Error", "Invalid cost value")
            return
        
        component_id = self.db.add_component(mpn, mfg, desc, cat)
        
        if component_id and dist and cost is not None:
            self.db.add_component_source(component_id, dist, dpn, cost)
        
        if component_id:
            messagebox.showinfo("Success", f"Component {mpn} added successfully")
            self.comp_mpn_entry.delete(0, tk.END)
            self.comp_mfg_entry.delete(0, tk.END)
            self.comp_desc_entry.delete(0, tk.END)
            self.comp_cat_entry.delete(0, tk.END)
            self.comp_dist_entry.delete(0, tk.END)
            self.comp_dpn_entry.delete(0, tk.END)
            self.comp_cost_entry.delete(0, tk.END)
            self.refresh_components()
        else:
            messagebox.showinfo("Info", "Component may already exist")
    
    def refresh_products(self):
        """Refresh the products list"""
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
        
        products = self.db.get_all_products()
        for product in products:
            self.product_tree.insert('', 'end', values=(
                product['part_number'],
                product['description'],
                product['revision'],
                product['created_date'][:10] if product['created_date'] else '',
                product['modified_date'][:10] if product['modified_date'] else ''
            ))
    
    def refresh_components(self):
        """Refresh the components list"""
        for item in self.component_tree.get_children():
            self.component_tree.delete(item)
        
        self.db.cursor.execute("""
            SELECT c.*, cs.distributor, cs.unit_cost
            FROM components c
            LEFT JOIN component_sources cs ON c.component_id = cs.component_id
            ORDER BY c.mfg_part_number
        """)
        components = self.db.cursor.fetchall()
        
        for comp in components:
            self.component_tree.insert('', 'end', values=(
                comp['mfg_part_number'],
                comp['manufacturer'],
                comp['description'],
                comp['category'],
                comp['distributor'] or '',
                f"${comp['unit_cost']:.2f}" if comp['unit_cost'] else ''
            ))
    
    def refresh_bom_products(self):
        """Refresh product lists in BOM tab"""
        products = self.db.get_all_products()
        product_list = [f"{p['part_number']} - {p['description']}" for p in products]
        
        self.bom_product_combo['values'] = product_list
        self.bom_sub_combo['values'] = product_list
        
        # Refresh components
        self.db.cursor.execute("SELECT * FROM components ORDER BY mfg_part_number")
        components = self.db.cursor.fetchall()
        component_list = [f"{c['mfg_part_number']} ({c['manufacturer']})" for c in components]
        self.bom_comp_combo['values'] = component_list
    
    def load_bom(self, event=None):
        """Load BOM for selected product"""
        selected = self.bom_product_var.get()
        if not selected:
            return
        
        part_number = selected.split(' - ')[0]
        product = self.db.get_product(part_number)
        
        if not product:
            return
        
        # Clear existing items
        for item in self.bom_tree.get_children():
            self.bom_tree.delete(item)
        
        # Load BOM
        components, sub_assemblies = self.db.get_product_bom(product['product_id'])
        
        # Add components
        for comp in components:
            cost_str = f"${comp['unit_cost']:.2f}" if comp['unit_cost'] else ''
            self.bom_tree.insert('', 'end', values=(
                'Component',
                comp['mfg_part_number'],
                comp['manufacturer'],
                comp['description'],
                comp['quantity'],
                comp['reference_designators'],
                comp['distributor'] or '',
                cost_str
            ))
        
        # Add sub-assemblies
        for sub in sub_assemblies:
            self.bom_tree.insert('', 'end', values=(
                'Sub-Assembly',
                sub['part_number'],
                'Assembly',
                sub['description'],
                sub['quantity'],
                sub['reference_designators'],
                '',
                ''
            ))
    
    def add_to_bom(self):
        """Add component to BOM"""
        product_str = self.bom_product_var.get()
        component_str = self.bom_comp_var.get()
        
        if not product_str or not component_str:
            messagebox.showerror("Error", "Please select product and component")
            return
        
        try:
            qty = float(self.bom_comp_qty_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return
        
        part_number = product_str.split(' - ')[0]
        product = self.db.get_product(part_number)
        
        # Extract component info
        mpn = component_str.split(' (')[0]
        mfg = component_str.split('(')[1].rstrip(')')
        
        self.db.cursor.execute("""
            SELECT component_id FROM components 
            WHERE mfg_part_number = ? AND manufacturer = ?
        """, (mpn, mfg))
        component = self.db.cursor.fetchone()
        
        if product and component:
            ref_des = self.bom_comp_ref_entry.get().strip()
            self.db.add_bom_entry(product['product_id'], component['component_id'], 
                                 qty, ref_des)
            messagebox.showinfo("Success", "Component added to BOM")
            self.bom_comp_qty_entry.delete(0, tk.END)
            self.bom_comp_qty_entry.insert(0, "1")
            self.bom_comp_ref_entry.delete(0, tk.END)
            self.load_bom()
    
    def add_subassembly_to_bom(self):
        """Add sub-assembly to BOM"""
        product_str = self.bom_product_var.get()
        sub_str = self.bom_sub_var.get()
        
        if not product_str or not sub_str:
            messagebox.showerror("Error", "Please select parent product and sub-assembly")
            return
        
        try:
            qty = float(self.bom_sub_qty_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return
        
        parent_pn = product_str.split(' - ')[0]
        child_pn = sub_str.split(' - ')[0]
        
        if parent_pn == child_pn:
            messagebox.showerror("Error", "Cannot add product to itself")
            return
        
        parent_product = self.db.get_product(parent_pn)
        child_product = self.db.get_product(child_pn)
        
        if parent_product and child_product:
            ref_des = self.bom_sub_ref_entry.get().strip()
            self.db.add_sub_assembly(parent_product['product_id'], 
                                    child_product['product_id'], qty, ref_des)
            messagebox.showinfo("Success", "Sub-assembly added to BOM")
            self.bom_sub_qty_entry.delete(0, tk.END)
            self.bom_sub_qty_entry.insert(0, "1")
            self.bom_sub_ref_entry.delete(0, tk.END)
            self.load_bom()
    
    def refresh_cost_products(self):
        """Refresh product list in cost tab"""
        products = self.db.get_all_products()
        product_list = [f"{p['part_number']} - {p['description']}" for p in products]
        self.cost_product_combo['values'] = product_list
    
    def calculate_cost(self):
        """Calculate and display cost breakdown"""
        selected = self.cost_product_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select a product")
            return
        
        try:
            qty = int(self.cost_qty_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return
        
        part_number = selected.split(' - ')[0]
        product = self.db.get_product(part_number)
        
        if not product:
            return
        
        # Calculate cost
        total_cost, breakdown = self.db.calculate_bom_cost(product['product_id'], qty)
        
        # Update display
        self.total_cost_label.config(text=f"${total_cost:.2f}")
        
        # Clear tree
        for item in self.cost_tree.get_children():
            self.cost_tree.delete(item)
        
        # Add breakdown
        for item in breakdown:
            self.cost_tree.insert('', 'end', values=(
                item['item'],
                f"{item['quantity']:.2f}",
                f"${item['unit_cost']:.4f}",
                f"${item['total']:.2f}"
            ))
    
    def export_flattened_bom(self):
        """Export flattened BOM to CSV"""
        selected = self.cost_product_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select a product")
            return
        
        try:
            qty = int(self.cost_qty_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return
        
        part_number = selected.split(' - ')[0]
        product = self.db.get_product(part_number)
        
        if not product:
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{part_number}_flattened_bom.csv"
        )
        
        if not filename:
            return
        
        flattened = self.db.get_flattened_bom(product['product_id'], qty)
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Mfg Part Number', 'Manufacturer', 'Description', 'Category',
                           'Total Quantity', 'Unit Cost', 'Total Cost', 'Distributor',
                           'Distributor Part Number'])
            
            for item in flattened:
                total_cost = float(item['unit_cost']) * item['quantity'] if item['unit_cost'] else 0
                writer.writerow([
                    item['mfg_part_number'],
                    item['manufacturer'],
                    item['description'],
                    item['category'],
                    item['quantity'],
                    item['unit_cost'] or '',
                    f"{total_cost:.2f}" if item['unit_cost'] else '',
                    item['distributor'] or '',
                    item['distributor_part_number'] or ''
                ])
        
        messagebox.showinfo("Success", f"Flattened BOM exported to {filename}")
    
    def import_bom_csv(self):
        """Import BOM from CSV file"""
        filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        # Show dialog to select product
        products = self.db.get_all_products()
        if not products:
            messagebox.showerror("Error", "No products exist. Create a product first.")
            return
        
        # Simple dialog to select product (you could enhance this)
        messagebox.showinfo("Import", 
                          "CSV should have columns: mfg_part_number, manufacturer, description, "
                          "category, quantity, distributor, unit_cost, reference_designators")
        
        messagebox.showinfo("Note", "Import feature requires product selection - "
                          "this is a basic implementation. Enhance as needed.")
    
    def export_bom_csv(self):
        """Export BOM to CSV file"""
        selected = self.bom_product_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select a product in the BOM Editor tab first")
            return
        
        part_number = selected.split(' - ')[0]
        product = self.db.get_product(part_number)
        
        if not product:
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{part_number}_bom.csv"
        )
        
        if not filename:
            return
        
        components, sub_assemblies = self.db.get_product_bom(product['product_id'])
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Part Number', 'Manufacturer/Product', 'Description',
                           'Quantity', 'Ref Des', 'Distributor', 'Unit Cost'])
            
            for comp in components:
                writer.writerow([
                    'Component',
                    comp['mfg_part_number'],
                    comp['manufacturer'],
                    comp['description'],
                    comp['quantity'],
                    comp['reference_designators'],
                    comp['distributor'] or '',
                    comp['unit_cost'] or ''
                ])
            
            for sub in sub_assemblies:
                writer.writerow([
                    'Sub-Assembly',
                    sub['part_number'],
                    'Assembly',
                    sub['description'],
                    sub['quantity'],
                    sub['reference_designators'],
                    '',
                    ''
                ])
        
        messagebox.showinfo("Success", f"BOM exported to {filename}")


def main():
    root = tk.Tk()
    app = BOMManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
