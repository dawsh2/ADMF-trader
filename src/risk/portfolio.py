@ObjectRegistry.register
class Position:
    # ... position implementation ...
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "cost_basis": self.cost_basis,
            "realized_pnl": self.realized_pnl
        }
    
    @classmethod
    def from_dict(cls, data):
        """Reconstruct from dictionary."""
        position = cls(data["symbol"])
        position.quantity = data["quantity"]
        position.cost_basis = data["cost_basis"]
        position.realized_pnl = data["realized_pnl"]
        return positio
