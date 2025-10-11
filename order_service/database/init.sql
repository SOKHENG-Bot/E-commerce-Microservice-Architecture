-- ==============================================
-- Order Service Database
-- ==============================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================
-- TABLES
-- ==============================================

-- Orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL, -- Reference to user service (no FK in microservices)
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) DEFAULT 0 NOT NULL,
    shipping_cost DECIMAL(10, 2) DEFAULT 0 NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0 NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
    billing_address JSONB NOT NULL,
    shipping_address JSONB NOT NULL,
    shipping_method VARCHAR(100),
    order_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    shipped_date TIMESTAMP WITH TIME ZONE,
    delivered_date TIMESTAMP WITH TIME ZONE,
    canceled_date TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    internal_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Order Items
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL, -- Reference to product service (no FK in microservices)
    variant_id INTEGER, -- Reference to product service (no FK in microservices)
    product_name VARCHAR(255) NOT NULL,
    product_sku VARCHAR(100),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    product_snapshot JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Payments
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_provider VARCHAR(50),
    provider_transaction_id VARCHAR(100),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
    gateway_response JSONB,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Shippings
CREATE TABLE shippings (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    tracking_number VARCHAR(100),
    carrier VARCHAR(100),
    status VARCHAR(20) DEFAULT 'preparing' NOT NULL,
    shipped_date TIMESTAMP WITH TIME ZONE,
    estimated_delivery_date TIMESTAMP WITH TIME ZONE,
    delivered_date TIMESTAMP WITH TIME ZONE,
    shipping_address JSONB NOT NULL,
    tracking_events JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================
-- INDEXES
-- ==============================================

CREATE INDEX idx_orders_order_number ON orders(order_number);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_order_date ON orders(order_date);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_order_items_variant_id ON order_items(variant_id);

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_provider_transaction_id ON payments(provider_transaction_id);

CREATE INDEX idx_shippings_order_id ON shippings(order_id);
CREATE INDEX idx_shippings_tracking_number ON shippings(tracking_number);
CREATE INDEX idx_shippings_status ON shippings(status);

-- ==============================================
-- TRIGGERS
-- ==============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_orders BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_order_items BEFORE UPDATE ON order_items FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_payments BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_shippings BEFORE UPDATE ON shippings FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ==============================================
-- SAMPLE DATA
-- ==============================================

-- Sample Orders
INSERT INTO orders (
    order_number, user_id, status, subtotal, tax_amount, shipping_cost,
    discount_amount, total_amount, currency, billing_address, shipping_address,
    shipping_method, notes
) VALUES
(
    'ORD-2025-001',
    1,
    'delivered',
    299.99,
    24.00,
    9.99,
    0.00,
    333.98,
    'USD',
    '{"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001", "country": "USA"}',
    '{"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001", "country": "USA"}',
    'standard',
    'First sample order'
),
(
    'ORD-2025-002',
    2,
    'processing',
    149.50,
    12.00,
    7.99,
    5.00,
    164.49,
    'USD',
    '{"street": "456 Oak Ave", "city": "Los Angeles", "state": "CA", "zip": "90210", "country": "USA"}',
    '{"street": "456 Oak Ave", "city": "Los Angeles", "state": "CA", "zip": "90210", "country": "USA"}',
    'express',
    'Second sample order with discount'
);

-- Sample Order Items
INSERT INTO order_items (
    order_id, product_id, variant_id, product_name, product_sku,
    quantity, unit_price, total_price, product_snapshot
) VALUES
(
    1,
    1,
    NULL,
    'MacBook Pro',
    'MBP-001',
    1,
    299.99,
    299.99,
    '{"name": "MacBook Pro", "sku": "MBP-001", "price": 299.99, "category": "Laptops"}'
),
(
    2,
    2,
    1,
    'iPhone 15',
    'IPH-001-BLK',
    1,
    149.50,
    149.50,
    '{"name": "iPhone 15", "sku": "IPH-001-BLK", "price": 149.50, "color": "Black", "category": "Phones"}'
);

-- Sample Payments
INSERT INTO payments (
    order_id, status, payment_method, payment_provider,
    provider_transaction_id, amount, currency, processed_at
) VALUES
(
    1,
    'completed',
    'credit_card',
    'stripe',
    'txn_1234567890',
    333.98,
    'USD',
    CURRENT_TIMESTAMP - INTERVAL '2 days'
),
(
    2,
    'completed',
    'paypal',
    'paypal',
    'PAY-9876543210',
    164.49,
    'USD',
    CURRENT_TIMESTAMP - INTERVAL '1 day'
);

-- Sample Shippings
INSERT INTO shippings (
    order_id, tracking_number, carrier, status, shipped_date,
    estimated_delivery_date, shipping_address
) VALUES
(
    1,
    'TRK123456789',
    'UPS',
    'delivered',
    CURRENT_TIMESTAMP - INTERVAL '3 days',
    CURRENT_TIMESTAMP - INTERVAL '1 day',
    '{"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001", "country": "USA"}'
),
(
    2,
    'TRK987654321',
    'FedEx',
    'shipped',
    CURRENT_TIMESTAMP - INTERVAL '1 day',
    CURRENT_TIMESTAMP + INTERVAL '2 days',
    '{"street": "456 Oak Ave", "city": "Los Angeles", "state": "CA", "zip": "90210", "country": "USA"}'
);

-- ==============================================
-- DONE
-- ==============================================

SELECT '✅ Order Service Database ready!' as status;