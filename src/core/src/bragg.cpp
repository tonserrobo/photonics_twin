#include "photonics/bragg.hpp"
#include <complex>
#include <utility>
#include <vector>

namespace photonics {

BraggGrating::BraggGrating(Material high, Material low,
                           real_t centre_nm, std::size_t periods)
    : high_(std::move(high)), low_(std::move(low)),
      centre_nm_(centre_nm), periods_(periods) {
    rebuild_stack_();
}

void BraggGrating::set_centre_nm(real_t v) { centre_nm_ = v; rebuild_stack_(); }
void BraggGrating::set_periods(std::size_t v) { periods_ = v; rebuild_stack_(); }
void BraggGrating::set_temperature_c(real_t v) {
    temperature_c_ = v;
    rebuild_stack_();
}
void BraggGrating::set_strain_microstrain(real_t v) {
    strain_microstrain_ = v;
    rebuild_stack_();
}

void BraggGrating::rebuild_stack_() {
    cached_stack_ = LayerStack{};
    cached_stack_.set_temperature_c(temperature_c_);

    // Thicknesses are fixed at the reference state and then expanded thermally
    // and elastically. Recomputing them from n(T) would cancel the index shift.
    const real_t delta_t = temperature_c_ - T_REF_C;
    const real_t strain_scale = real_t{1.0} + strain_microstrain_ * real_t{1e-6};
    const real_t t_h_ref = centre_nm_ / (real_t{4.0} * high_.n(centre_nm_, T_REF_C));
    const real_t t_l_ref = centre_nm_ / (real_t{4.0} * low_.n(centre_nm_, T_REF_C));
    const real_t t_h = t_h_ref * (real_t{1.0} + high_.cte() * delta_t) * strain_scale;
    const real_t t_l = t_l_ref * (real_t{1.0} + low_.cte() * delta_t) * strain_scale;
    for (std::size_t i = 0; i < periods_; ++i) {
        cached_stack_.add_layer(t_h, high_);
        cached_stack_.add_layer(t_l, low_);
    }
}

void BraggGrating::reflectance(const real_t* wl, std::size_t n_wl,
                               real_t* R_out) const {
    std::vector<complex_t> r(n_wl), t(n_wl);
    tmm_sweep(cached_stack_, wl, n_wl, r.data(), t.data());
    for (std::size_t i = 0; i < n_wl; ++i) {
        R_out[i] = std::norm(r[i]);
    }
}

}  // namespace photonics
