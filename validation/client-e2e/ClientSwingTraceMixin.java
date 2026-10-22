package validation.mixin;

import dev.companion.minecraft.CompanionEntity;
import net.minecraft.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** CI-only probes at the vanilla client entity-status and swing-tick boundaries. */
@Mixin(LivingEntity.class)
abstract class ClientSwingTraceMixin {
    @Unique private int ci$lastLoggedSwingTick = Integer.MIN_VALUE;
    @Unique private boolean ci$lastLoggedSwinging;

    @Inject(method = "handleStatus", at = @At("TAIL"))
    private void ci$afterStatus(byte status, CallbackInfo ci) {
        if ((Object) this instanceof CompanionEntity companion && (status == 0 || status == 3)) {
            validation.CiClientValidation.trace("CI_SWING_STATUS_RECEIVED side="
                    + (companion.getWorld().isClient ? "CLIENT" : "SERVER")
                    + " status=" + status + " entityId=" + companion.getId()
                    + " uuid=" + companion.getUuid() + " age=" + companion.age
                    + " handSwinging=" + companion.handSwinging
                    + " handSwingTicks=" + companion.handSwingTicks
                    + " progress=" + companion.getHandSwingProgress(1.0F));
        }
    }

    @Inject(method = "tickHandSwing", at = @At("TAIL"))
    private void ci$afterSwingTick(CallbackInfo ci) {
        if ((Object) this instanceof CompanionEntity companion && companion.getWorld().isClient) {
            int ticks = companion.handSwingTicks;
            boolean swinging = companion.handSwinging;
            if (ticks != ci$lastLoggedSwingTick || swinging != ci$lastLoggedSwinging) {
                ci$lastLoggedSwingTick = ticks;
                ci$lastLoggedSwinging = swinging;
                validation.CiClientValidation.trace("CI_SWING_CLIENT_TICK entityId="
                        + companion.getId() + " uuid=" + companion.getUuid()
                        + " age=" + companion.age + " handSwinging=" + swinging
                        + " handSwingTicks=" + ticks
                        + " progress=" + companion.getHandSwingProgress(1.0F));
            }
        }
    }
}
