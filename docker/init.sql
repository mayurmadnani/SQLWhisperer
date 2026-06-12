-- Bootstrap data for the Agentic SQL demo

DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agentic') THEN
        CREATE ROLE agentic WITH LOGIN PASSWORD 'agentic';
    ELSE
        ALTER ROLE agentic WITH LOGIN PASSWORD 'agentic';
    END IF;
END
$$;

SELECT 'CREATE DATABASE agenticdb OWNER agentic'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'agenticdb')
\gexec

GRANT ALL PRIVILEGES ON DATABASE agenticdb TO agentic;
\connect agenticdb

ALTER SCHEMA public OWNER TO agentic;
GRANT USAGE ON SCHEMA public TO agentic;
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM agentic;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agentic;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE INSERT, UPDATE, DELETE ON TABLES FROM agentic;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agentic;
SET ROLE agentic;

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    loyalty_tier TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    order_date DATE NOT NULL,
    quantity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    topic TEXT NOT NULL,
    created_at DATE NOT NULL,
    status TEXT NOT NULL
);

INSERT INTO customers (customer_id, name, city, loyalty_tier) VALUES
    (1, 'Avery Chen', 'San Francisco', 'Gold'),
    (2, 'Jordan Patel', 'Austin', 'Silver'),
    (3, 'Kai Rodriguez', 'New York', 'Platinum'),
    (4, 'Morgan Blake', 'Seattle', 'Bronze'),
    (5, 'Samira Ali', 'Chicago', 'Gold'),
    (6, 'Noah Singh', 'Boston', 'Silver')
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO products (product_id, name, category, unit_price) VALUES
    (101, 'Horizon Speaker', 'Audio', 149.00),
    (102, 'Aurora Headphones', 'Audio', 99.00),
    (103, 'Nimbus Laptop', 'Computing', 1299.00),
    (104, 'Pulse Smartwatch', 'Wearable', 199.00),
    (105, 'Flux Tablet', 'Computing', 699.00)
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO orders (order_id, customer_id, product_id, order_date, quantity) VALUES
    (1001, 1, 103, '2024-09-12', 1),
    (1002, 2, 104, '2024-09-13', 2),
    (1003, 3, 101, '2024-09-15', 3),
    (1004, 1, 102, '2024-10-01', 1),
    (1005, 4, 105, '2024-10-05', 1),
    (1006, 5, 101, '2024-10-05', 2),
    (1007, 6, 104, '2024-10-07', 1),
    (1008, 3, 105, '2024-10-08', 1)
ON CONFLICT (order_id) DO NOTHING;

INSERT INTO support_tickets (ticket_id, customer_id, topic, created_at, status) VALUES
    (201, 1, 'Shipping', '2024-09-18', 'Resolved'),
    (202, 3, 'Technical', '2024-09-20', 'Open'),
    (203, 2, 'Return', '2024-09-22', 'Resolved'),
    (204, 5, 'Billing', '2024-10-02', 'Open'),
    (205, 6, 'Technical', '2024-10-04', 'Resolved')
ON CONFLICT (ticket_id) DO NOTHING;
