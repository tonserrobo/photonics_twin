// src/core/include/photonics/tmm.hpp
#pragma once
#include <vector>
#include "photonics/common.hpp"
#include "photonics/materials.hpp"

namespace photonics {

struct Layer {
    real_t thickness_nm;
    const Material* material;
};

class LayerStack {
public:
    void add_layer(real_t thickness_nm, const Material& m);
    std::size_t size() const { return layers_.size(); }
    const Layer& at(std::size_t i) const { return layers_.at(i); }

private:
    std::vector<Layer> layers_;
};

// Free function — the HLS synthesis target.
// Computes complex r and t at each wavelength for normal-incidence light
// entering from vacuum (n=1) into the stack with vacuum behind it.
void tmm_sweep(const LayerStack& stack,
               const real_t* wavelengths_nm, std::size_t n_wl,
               complex_t* r_out, complex_t* t_out);

}  // namespace photonics
