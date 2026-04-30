// src/core/include/photonics/bragg.hpp
#pragma once
#include "photonics/tmm.hpp"
#include "photonics/materials.hpp"

namespace photonics {

class BraggGrating {
public:
    BraggGrating(Material high, Material low, real_t centre_nm, std::size_t periods);

    void set_centre_nm(real_t v);
    void set_periods(std::size_t v);

    real_t      centre_nm() const { return centre_nm_; }
    std::size_t periods()   const { return periods_; }

    const LayerStack& stack() const { return cached_stack_; }

    // Reflectance |r|^2 at each input wavelength.
    void reflectance(const real_t* wavelengths_nm, std::size_t n_wl,
                     real_t* R_out) const;

private:
    void rebuild_stack_();

    Material high_;
    Material low_;
    real_t   centre_nm_;
    std::size_t periods_;
    LayerStack cached_stack_;
};

}  // namespace photonics
