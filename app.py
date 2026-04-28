class RetirementModel:
    def __init__(self, current_isa, current_sipp, annual_spend, growth_rate, inflation):
        self.isa = current_isa
        self.sipp = current_sipp
        self.annual_spend = annual_spend
        self.growth = growth_rate
        self.inflation = inflation

    def calculate_year(self):
        # Grow assets
        self.isa *= (1 + self.growth)
        self.sipp *= (1 + self.growth)
        
        # Withdraw strategy: ISA first
        if self.isa >= self.annual_spend:
            self.isa -= self.annual_spend
        else:
            remaining = self.annual_spend - self.isa
            self.isa = 0
            self.sipp -= remaining # Tax logic would be applied here
            
        # Adjust spend for next year
        self.annual_spend *= (1 + self.inflation)

