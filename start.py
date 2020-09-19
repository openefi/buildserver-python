#!/usr/bin/env python3

from app import app
import sys

if len(sys.argv) > 1 and sys.argv[1] == 'db':
    from app import models
    with app.app_context():
        models.Build.create_table(True)

if __name__ == "__main__":
    app.run(debug=True)