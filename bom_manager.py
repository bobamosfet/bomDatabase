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
        # Check if this source already exists
        self.cursor.execute("""
            SELECT source_id FROM component_sources 
            WHERE component_id = ? AND distributor = ?
        """, (component_id, distributor))
        
        existing = self.cursor.fetchone()
        
        if existing:
            # Update existing source instead of creating duplicate
            now = datetime.now().isoformat()
            self.cursor.execute("""
                UPDATE component_sources 
                SET distributor_part_number = ?,
                    unit_cost = ?,
                    minimum_order_qty = ?,
                    lead_time_days = ?,
                    last_updated = ?
                WHERE source_id = ?
            """, (distributor_part_number, unit_cost, minimum_order_qty, 
                  lead_time_days, now, existing['source_id']))
            self.conn.commit()
            return existing['source_id']
        else:
            # Create new source
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
                c.component_id,
                be.entry_id,
                c.mfg_part_number,
                c.manufacturer,
                c.description,
                c.category,
                c.unit_of_measure,
                be.quantity,
                be.reference_designators,
                be.do_not_populate,
                be.notes,
                (SELECT distributor FROM component_sources 
                 WHERE component_id = c.component_id 
                 ORDER BY unit_cost ASC LIMIT 1) as distributor,
                (SELECT distributor_part_number FROM component_sources 
                 WHERE component_id = c.component_id 
                 ORDER BY unit_cost ASC LIMIT 1) as distributor_part_number,
                (SELECT unit_cost FROM component_sources 
                 WHERE component_id = c.component_id 
                 ORDER BY unit_cost ASC LIMIT 1) as unit_cost,
                (SELECT minimum_order_qty FROM component_sources 
                 WHERE component_id = c.component_id 
                 ORDER BY unit_cost ASC LIMIT 1) as minimum_order_qty,
                (SELECT lead_time_days FROM component_sources 
                 WHERE component_id = c.component_id 
                 ORDER BY unit_cost ASC LIMIT 1) as lead_time_days,
                'component' as item_type
            FROM bom_entries be
            JOIN components c ON be.component_id = c.component_id
            WHERE be.product_id = ? {dnp_filter}
            ORDER BY be.reference_designators, c.mfg_part_number
        """, (product_id,))
        components = self.cursor.fetchall()
        
        # Get sub-assemblies
        self.cursor.execute("""
            SELECT 
                sa.sub_assembly_id,
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
            sub_cost, sub_breakdown = self.calculate_bom_cost(sub['product_id'], 
                                                   float(sub['quantity']) * quantity, 
                                                   include_dnp)
            total_cost += sub_cost
            
            # Calculate per-unit cost (handle zero quantity gracefully)
            if float(sub['quantity']) * quantity > 0:
                unit_cost = sub_cost / (float(sub['quantity']) * quantity)
            else:
                unit_cost = 0.0
            
            component_costs.append({
                'item': f"[SUB-ASSEMBLY] {sub['part_number']} - {sub['description']}",
                'quantity': sub['quantity'],
                'unit_cost': unit_cost,
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
    
    def delete_bom_entry(self, entry_id):
        """Delete a BOM entry (component from a product)"""
        self.cursor.execute("DELETE FROM bom_entries WHERE entry_id = ?", (entry_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_sub_assembly_entry(self, sub_assembly_id):
        """Delete a sub-assembly entry (product from another product)"""
        self.cursor.execute("DELETE FROM sub_assemblies WHERE sub_assembly_id = ?", (sub_assembly_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_entire_bom(self, product_id):
        """Delete all BOM entries and sub-assemblies for a product"""
        # Delete all component entries
        self.cursor.execute("DELETE FROM bom_entries WHERE product_id = ?", (product_id,))
        components_deleted = self.cursor.rowcount
        
        # Delete all sub-assembly entries
        self.cursor.execute("DELETE FROM sub_assemblies WHERE parent_product_id = ?", (product_id,))
        subs_deleted = self.cursor.rowcount
        
        self.conn.commit()
        return components_deleted + subs_deleted
    
    def get_bom_entry_id(self, product_id, component_id):
        """Get the entry_id for a specific component in a product's BOM"""
        self.cursor.execute("""
            SELECT entry_id FROM bom_entries 
            WHERE product_id = ? AND component_id = ?
        """, (product_id, component_id))
        result = self.cursor.fetchone()
        return result['entry_id'] if result else None
    
    def get_sub_assembly_entry_id(self, parent_product_id, child_product_id):
        """Get the sub_assembly_id for a specific sub-assembly relationship"""
        self.cursor.execute("""
            SELECT sub_assembly_id FROM sub_assemblies 
            WHERE parent_product_id = ? AND child_product_id = ?
        """, (parent_product_id, child_product_id))
        result = self.cursor.fetchone()
        return result['sub_assembly_id'] if result else None
    
    def cleanup_duplicate_sources(self):
        """Remove duplicate component sources, keeping the most recent one"""
        # Find duplicates (same component_id + distributor)
        self.cursor.execute("""
            SELECT component_id, distributor, COUNT(*) as count
            FROM component_sources
            GROUP BY component_id, distributor
            HAVING count > 1
        """)
        duplicates = self.cursor.fetchall()
        
        removed_count = 0
        for dup in duplicates:
            # Keep the most recent one, delete the rest
            self.cursor.execute("""
                SELECT source_id FROM component_sources
                WHERE component_id = ? AND distributor = ?
                ORDER BY last_updated DESC
            """, (dup['component_id'], dup['distributor']))
            
            all_sources = self.cursor.fetchall()
            # Keep first (most recent), delete others
            for source in all_sources[1:]:
                self.cursor.execute("DELETE FROM component_sources WHERE source_id = ?", 
                                  (source['source_id'],))
                removed_count += 1
        
        self.conn.commit()
        return removed_count
    
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
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Clean Up Duplicate Components", command=self.cleanup_duplicates)
        
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
        
        # Button frame for BOM operations
        bom_btn_frame = ttk.Frame(bottom_frame)
        bom_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(bom_btn_frame, text="Delete Selected Item", 
                  command=self.delete_bom_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(bom_btn_frame, text="Clear Entire BOM", 
                  command=self.clear_entire_bom).pack(side=tk.LEFT, padx=5)
        ttk.Label(bom_btn_frame, text="(Select an item in the list above to delete it)", 
                 foreground='gray').pack(side=tk.LEFT, padx=20)
        
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
        
        ttk.Button(top_frame, text="Refresh Products", 
                  command=self.refresh_cost_products).grid(row=0, column=5, padx=5)
        
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
        
        # Check if component already exists
        self.db.cursor.execute("""
            SELECT component_id FROM components 
            WHERE mfg_part_number = ? AND manufacturer = ?
        """, (mpn, mfg))
        existing_component = self.db.cursor.fetchone()
        
        component_id = self.db.add_component(mpn, mfg, desc, cat)
        
        message = ""
        if existing_component:
            message = f"Component {mpn} already exists. "
        else:
            message = f"Component {mpn} added successfully. "
        
        if component_id and dist and cost is not None:
            # Check if this distributor source already exists
            self.db.cursor.execute("""
                SELECT source_id FROM component_sources 
                WHERE component_id = ? AND distributor = ?
            """, (component_id, dist))
            existing_source = self.db.cursor.fetchone()
            
            self.db.add_component_source(component_id, dist, dpn, cost)
            
            if existing_source:
                message += f"Updated pricing from {dist}."
            else:
                message += f"Added distributor {dist}."
        
        messagebox.showinfo("Success", message)
        self.comp_mpn_entry.delete(0, tk.END)
        self.comp_mfg_entry.delete(0, tk.END)
        self.comp_desc_entry.delete(0, tk.END)
        self.comp_cat_entry.delete(0, tk.END)
        self.comp_dist_entry.delete(0, tk.END)
        self.comp_dpn_entry.delete(0, tk.END)
        self.comp_cost_entry.delete(0, tk.END)
        self.refresh_components()
    
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
        
        # Store current product_id for later use
        self.current_bom_product_id = product['product_id']
        
        # Dictionary to store item metadata (maps tree item_id to database ID)
        self.bom_item_metadata = {}
        
        # Clear existing items
        for item in self.bom_tree.get_children():
            self.bom_tree.delete(item)
        
        # Load BOM
        components, sub_assemblies = self.db.get_product_bom(product['product_id'])
        
        # DEBUG: Print what we got
        print(f"DEBUG: Loading BOM for product_id {product['product_id']}")
        print(f"DEBUG: Found {len(components)} components")
        print(f"DEBUG: Found {len(sub_assemblies)} sub-assemblies")
        
        # Add components - use entry_id from query results
        for idx, comp in enumerate(components):
            try:
                print(f"DEBUG: Component {idx}: {comp['mfg_part_number']} - entry_id: {comp['entry_id']}")
                
                cost_str = f"${comp['unit_cost']:.2f}" if comp['unit_cost'] else ''
                
                item_id = self.bom_tree.insert('', 'end', values=(
                    'Component',
                    comp['mfg_part_number'],
                    comp['manufacturer'],
                    comp['description'],
                    comp['quantity'],
                    comp['reference_designators'],
                    comp['distributor'] or '',
                    cost_str
                ))
                # Store metadata in dictionary
                self.bom_item_metadata[item_id] = ('component', comp['entry_id'])
            except Exception as e:
                print(f"ERROR loading component {idx}: {e}")
                raise
        
        # Add sub-assemblies - use sub_assembly_id from query results
        for idx, sub in enumerate(sub_assemblies):
            print(f"DEBUG: Sub-assembly {idx}: {sub['part_number']} - sub_assembly_id: {sub['sub_assembly_id']}")
            item_id = self.bom_tree.insert('', 'end', values=(
                'Sub-Assembly',
                sub['part_number'],
                'Assembly',
                sub['description'],
                sub['quantity'],
                sub['reference_designators'],
                '',
                ''
            ))
            # Store metadata in dictionary
            self.bom_item_metadata[item_id] = ('subassembly', sub['sub_assembly_id'])
        
        print(f"DEBUG: Total items in tree: {len(self.bom_tree.get_children())}")
    
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
            # Check for duplicate
            self.db.cursor.execute("""
                SELECT entry_id FROM bom_entries 
                WHERE product_id = ? AND component_id = ?
            """, (product['product_id'], component['component_id']))
            
            if self.db.cursor.fetchone():
                messagebox.showerror("Duplicate Entry", 
                    f"Component {mpn} ({mfg}) is already in this BOM.\n\n"
                    "To change quantity or reference designators, delete the existing entry first.")
                return
            
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
            # Check for duplicate
            self.db.cursor.execute("""
                SELECT sub_assembly_id FROM sub_assemblies 
                WHERE parent_product_id = ? AND child_product_id = ?
            """, (parent_product['product_id'], child_product['product_id']))
            
            if self.db.cursor.fetchone():
                messagebox.showerror("Duplicate Entry", 
                    f"Sub-assembly {child_pn} is already in this BOM.\n\n"
                    "To change quantity or reference designators, delete the existing entry first.")
                return
            
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
    
    def delete_bom_item(self):
        """Delete selected BOM item"""
        selected = self.bom_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an item to delete")
            return
        
        # Get the item's metadata from dictionary
        item_id = selected[0]
        
        if item_id not in self.bom_item_metadata:
            messagebox.showerror("Error", "Cannot find item metadata")
            return
        
        item_type, db_id = self.bom_item_metadata[item_id]
        
        # Get item info for confirmation
        values = self.bom_tree.item(item_id, 'values')
        item_name = f"{values[1]} ({values[2]})" if values else "this item"
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", 
                                   f"Delete {item_name} from this BOM?"):
            return
        
        # Delete from database
        success = False
        if item_type == 'component':
            success = self.db.delete_bom_entry(db_id)
        elif item_type == 'subassembly':
            success = self.db.delete_sub_assembly_entry(db_id)
        
        if success:
            messagebox.showinfo("Success", "Item deleted from BOM")
            self.load_bom()  # Refresh the display
        else:
            messagebox.showerror("Error", "Failed to delete item")
    
    def clear_entire_bom(self):
        """Clear all items from the current BOM"""
        if not hasattr(self, 'current_bom_product_id'):
            messagebox.showwarning("No Product", "Please select a product first")
            return
        
        selected = self.bom_product_var.get()
        if not selected:
            messagebox.showwarning("No Product", "Please select a product first")
            return
        
        part_number = selected.split(' - ')[0]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Clear BOM", 
                                   f"Are you sure you want to delete ALL components and sub-assemblies from {part_number}?\n\n"
                                   "This action cannot be undone!",
                                   icon='warning'):
            return
        
        # Delete from database
        count = self.db.delete_entire_bom(self.current_bom_product_id)
        
        if count > 0:
            messagebox.showinfo("Success", f"Deleted {count} items from BOM")
            self.load_bom()  # Refresh the display
        else:
            messagebox.showinfo("Info", "BOM is already empty")
    
    def cleanup_duplicates(self):
        """Clean up duplicate component sources"""
        if not messagebox.askyesno("Clean Up Duplicates", 
                                   "This will remove duplicate component sources (same component + distributor).\n\n"
                                   "The most recent entry for each duplicate will be kept.\n\n"
                                   "Continue?"):
            return
        
        count = self.db.cleanup_duplicate_sources()
        
        if count > 0:
            messagebox.showinfo("Cleanup Complete", 
                              f"Removed {count} duplicate component source(s).\n\n"
                              "The Components tab will now be refreshed.")
            self.refresh_components()
        else:
            messagebox.showinfo("No Duplicates", "No duplicate component sources found.")
    
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
            # Format differently for sub-assemblies vs components
            if '[SUB-ASSEMBLY]' in item['item']:
                # Sub-assemblies in bold (using tags)
                self.cost_tree.insert('', 'end', values=(
                    item['item'],
                    f"{item['quantity']:.2f}",
                    f"${item['unit_cost']:.4f}" if item['unit_cost'] > 0 else "Calculated",
                    f"${item['total']:.2f}"
                ), tags=('subassembly',))
            else:
                # Regular components
                self.cost_tree.insert('', 'end', values=(
                    item['item'],
                    f"{item['quantity']:.2f}",
                    f"${item['unit_cost']:.4f}",
                    f"${item['total']:.2f}"
                ))
        
        # Configure tags for better visibility
        self.cost_tree.tag_configure('subassembly', background='#e8f4f8')
    
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
        
        # Create product selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Product for Import")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select product to import BOM into:", 
                 font=('TkDefaultFont', 10)).pack(pady=10)
        
        product_var = tk.StringVar()
        product_combo = ttk.Combobox(dialog, textvariable=product_var,
                                     width=50, state='readonly')
        product_list = [f"{p['part_number']} - {p['description']}" for p in products]
        product_combo['values'] = product_list
        product_combo.pack(pady=10)
        
        selected_product = {'value': None}
        
        def on_ok():
            if not product_var.get():
                messagebox.showerror("Error", "Please select a product")
                return
            selected_product['value'] = product_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        
        if not selected_product['value']:
            return
        
        part_number = selected_product['value'].split(' - ')[0]
        product = self.db.get_product(part_number)
        
        if not product:
            return
        
        # Read and import CSV
        try:
            imported_count = 0
            skipped_count = 0
            
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Check for required columns
                required_cols = ['mfg_part_number', 'manufacturer', 'quantity']
                if not all(col in reader.fieldnames for col in required_cols):
                    messagebox.showerror("Error", 
                        f"CSV must contain columns: {', '.join(required_cols)}\n"
                        f"Found: {', '.join(reader.fieldnames)}")
                    return
                
                for row in reader:
                    try:
                        # Skip empty rows
                        if not row.get('mfg_part_number') or not row.get('manufacturer'):
                            continue
                        
                        # Add or get component
                        component_id = self.db.add_component(
                            row['mfg_part_number'].strip(),
                            row['manufacturer'].strip(),
                            row.get('description', '').strip(),
                            row.get('category', '').strip(),
                            row.get('unit_of_measure', 'EA').strip()
                        )
                        
                        if not component_id:
                            skipped_count += 1
                            continue
                        
                        # Add distributor source if provided
                        if row.get('distributor') and row.get('unit_cost'):
                            try:
                                unit_cost = float(row['unit_cost'])
                                self.db.add_component_source(
                                    component_id,
                                    row['distributor'].strip(),
                                    row.get('distributor_part_number', '').strip(),
                                    unit_cost,
                                    int(row.get('minimum_order_qty', 1)),
                                    int(row['lead_time_days']) if row.get('lead_time_days') else None
                                )
                            except (ValueError, KeyError):
                                pass  # Skip invalid cost data
                        
                        # Add to BOM - check for duplicates first
                        quantity = float(row['quantity'])
                        ref_des = row.get('reference_designators', '').strip()
                        notes = row.get('notes', '').strip()
                        
                        # Check if this component already exists in the BOM
                        self.db.cursor.execute("""
                            SELECT entry_id FROM bom_entries 
                            WHERE product_id = ? AND component_id = ?
                        """, (product['product_id'], component_id))
                        
                        existing = self.db.cursor.fetchone()
                        
                        if existing:
                            # Component already in BOM, skip it
                            skipped_count += 1
                            print(f"Skipped duplicate: {row['mfg_part_number']} ({row['manufacturer']})")
                            continue
                        
                        self.db.add_bom_entry(
                            product['product_id'],
                            component_id,
                            quantity,
                            ref_des,
                            notes=notes
                        )
                        
                        imported_count += 1
                        
                    except Exception as e:
                        print(f"Error importing row: {row}, Error: {e}")
                        skipped_count += 1
                        continue
            
            messagebox.showinfo("Import Complete", 
                f"Successfully imported {imported_count} components.\n"
                f"Skipped {skipped_count} items.")
            
            # Refresh displays
            self.refresh_components()
            if self.bom_product_var.get() and part_number in self.bom_product_var.get():
                self.load_bom()
                
        except Exception as e:
            messagebox.showerror("Import Error", f"Error reading CSV file:\n{str(e)}")
    
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
            # Header matches import format plus item_type to distinguish sub-assemblies
            writer.writerow(['item_type', 'mfg_part_number', 'manufacturer', 'description', 'category',
                           'quantity', 'reference_designators', 'distributor', 
                           'distributor_part_number', 'unit_cost', 'minimum_order_qty', 
                           'lead_time_days', 'notes'])
            
            for comp in components:
                writer.writerow([
                    'component',
                    comp['mfg_part_number'],
                    comp['manufacturer'],
                    comp['description'],
                    comp['category'],
                    comp['quantity'],
                    comp['reference_designators'],
                    comp['distributor'] or '',
                    comp['distributor_part_number'] or '',
                    comp['unit_cost'] or '',
                    comp['minimum_order_qty'] or '',
                    comp['lead_time_days'] or '',
                    comp['notes'] or ''
                ])
            
            # Include sub-assemblies in export
            for sub in sub_assemblies:
                writer.writerow([
                    'sub_assembly',
                    sub['part_number'],
                    'SUB-ASSEMBLY',
                    sub['description'],
                    'Assembly',
                    sub['quantity'],
                    sub['reference_designators'],
                    '',
                    '',
                    '',
                    '',
                    '',
                    sub['notes'] or ''
                ])
        
        messagebox.showinfo("Success", f"BOM exported to {filename}\n\nNote: Sub-assemblies are marked as 'sub_assembly' in the item_type column.")


def main():
    root = tk.Tk()
    app = BOMManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
