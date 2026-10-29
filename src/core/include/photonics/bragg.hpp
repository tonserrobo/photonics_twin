// src/core/include/photonics/bragg.hpp
#pragma once
#include <vector>
#include "photonics/tmm.hpp"
#include "photonics/materials.hpp"

namespace photonics {

class BraggGrating {
public:
    BraggGrating(Material high, Material low, real_t centre_nm, std::size_t periods);

    void set_centre_nm(real_t v);
    void set_periods(std::size_t v);
    void set_temperature_c(real_t v);
    void set_strain_microstrain(real_t v);
    void set_thickness_scales(const std::vector<real_t>& scales);
    void clear_thickness_scales();

    real_t      centre_nm() const { return centre_nm_; }
    std::size_t periods()   const { return periods_; }
    real_t      temperature_c() const { return temperature_c_; }
    real_t      strain_microstrain() const { return strain_microstrain_; }

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
    real_t   temperature_c_ = T_REF_C;
    real_t   strain_microstrain_ = 0.0;
    std::vector<real_t> thickness_scales_;
    LayerStack cached_stack_;
};

}  // namespace photonics
